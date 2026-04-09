"""
Listing Health Score API — read health scores and manage IDX feed configs.

Endpoints:
  GET  /listings/{id}/health           — score breakdown + trend
  GET  /listings/health/summary        — tenant-wide health overview
  GET  /admin/health/overview          — cross-tenant stats (admin only)
  POST /settings/idx-feed              — create IDX config (Pro+)
  GET  /settings/idx-feed              — list IDX configs
  PATCH /settings/idx-feed/{id}        — update config
  DELETE /settings/idx-feed/{id}       — remove config
  GET  /settings/health-weights        — current weights
  PATCH /settings/health-weights       — custom weights (Enterprise)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db, require_admin
from listingjet.api.schemas.health import (
    HealthBreakdown,
    HealthSubScoreDetail,
    HealthSummaryListing,
    HealthSummaryResponse,
    HealthTrendPoint,
    HealthWeightsResponse,
    HealthWeightsUpdate,
    IdxFeedConfigCreate,
    IdxFeedConfigResponse,
    IdxFeedConfigUpdate,
    ListingHealthResponse,
)
from listingjet.models.idx_feed_config import IdxFeedConfig
from listingjet.models.listing import Listing
from listingjet.models.listing_health_score import ListingHealthScore
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services import field_encryption
from listingjet.services import health_score as hs

router = APIRouter()


# ---- Health Score Endpoints ----


@router.get("/listings/{listing_id}/health")
async def get_listing_health(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListingHealthResponse:
    """Get health score breakdown + 90-day trend for a listing."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")

    score = await hs.get_score(db, listing_id)
    tenant = await db.get(Tenant, current_user.tenant_id)
    plan = tenant.plan if tenant else "starter"

    if not score:
        # Calculate on-demand if not yet computed
        score = await hs.calculate(
            session=db,
            listing_id=listing_id,
            tenant_id=current_user.tenant_id,
            plan=plan,
        )

    trend_data = await hs.get_trend(db, listing_id)

    # Build breakdown based on plan
    signals = score.signals_snapshot or {}
    weights = score.weights or {}
    breakdown = HealthBreakdown()

    if "media" in signals:
        breakdown.media_quality = HealthSubScoreDetail(
            score=signals["media"]["score"],
            weight=weights.get("media", 0.3),
            details=signals["media"]["details"],
        )
    if "content" in signals:
        breakdown.content_readiness = HealthSubScoreDetail(
            score=signals["content"]["score"],
            weight=weights.get("content", 0.2),
            details=signals["content"]["details"],
        )
    if "velocity" in signals and plan in ("active_agent", "pro", "team", "enterprise"):
        breakdown.pipeline_velocity = HealthSubScoreDetail(
            score=signals["velocity"]["score"],
            weight=weights.get("velocity", 0.15),
            details=signals["velocity"]["details"],
        )
    if "syndication" in signals and plan in ("active_agent", "pro", "team", "enterprise"):
        breakdown.syndication = HealthSubScoreDetail(
            score=signals["syndication"]["score"],
            weight=weights.get("syndication", 0.2),
            details=signals["syndication"]["details"],
        )
    if "market" in signals and plan in ("team", "enterprise"):
        breakdown.market_signal = HealthSubScoreDetail(
            score=signals["market"]["score"],
            weight=weights.get("market", 0.15),
            details=signals["market"]["details"],
        )

    return ListingHealthResponse(
        listing_id=listing_id,
        overall_score=score.overall_score,
        breakdown=breakdown,
        trend=[HealthTrendPoint(**t) for t in trend_data],
        calculated_at=score.calculated_at,
    )


@router.get("/listings/health/summary")
async def get_health_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthSummaryResponse:
    """Tenant-wide health overview: avg score, distribution, top/bottom."""
    result = await db.execute(
        select(ListingHealthScore).where(
            ListingHealthScore.tenant_id == current_user.tenant_id
        )
    )
    scores = result.scalars().all()

    if not scores:
        return HealthSummaryResponse(
            average_score=0,
            total_scored=0,
            distribution={"green": 0, "yellow": 0, "red": 0},
            top_listings=[],
            bottom_listings=[],
        )

    avg = sum(s.overall_score for s in scores) / len(scores)
    green = sum(1 for s in scores if s.overall_score >= 80)
    yellow = sum(1 for s in scores if 60 <= s.overall_score < 80)
    red = sum(1 for s in scores if s.overall_score < 60)

    # Top 5 and bottom 5
    sorted_scores = sorted(scores, key=lambda s: s.overall_score, reverse=True)

    async def _to_summary(s: ListingHealthScore) -> HealthSummaryListing:
        listing = await db.get(Listing, s.listing_id)
        return HealthSummaryListing(
            listing_id=s.listing_id,
            address=listing.address if listing else {},
            overall_score=s.overall_score,
        )

    top = [await _to_summary(s) for s in sorted_scores[:5]]
    bottom = [await _to_summary(s) for s in sorted_scores[-5:]] if len(sorted_scores) > 5 else []

    return HealthSummaryResponse(
        average_score=round(avg, 1),
        total_scored=len(scores),
        distribution={"green": green, "yellow": yellow, "red": red},
        top_listings=top,
        bottom_listings=bottom,
    )


@router.get("/admin/health/overview")
async def admin_health_overview(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cross-tenant health stats (admin only). Uses admin DB session."""
    from listingjet.database import AsyncSessionLocal

    async with AsyncSessionLocal() as admin_db:
        result = await admin_db.execute(
            select(
                ListingHealthScore.tenant_id,
                func.count().label("count"),
                func.avg(ListingHealthScore.overall_score).label("avg_score"),
                func.min(ListingHealthScore.overall_score).label("min_score"),
                func.max(ListingHealthScore.overall_score).label("max_score"),
            ).group_by(ListingHealthScore.tenant_id)
        )
        rows = result.all()

    return {
        "tenants": [
            {
                "tenant_id": str(row.tenant_id),
                "count": row.count,
                "avg_score": round(float(row.avg_score), 1) if row.avg_score else 0,
                "min_score": row.min_score,
                "max_score": row.max_score,
            }
            for row in rows
        ],
        "total_scored": sum(r.count for r in rows),
    }


# ---- IDX Feed Config Endpoints ----


@router.post("/settings/idx-feed", status_code=201)
async def create_idx_feed(
    body: IdxFeedConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IdxFeedConfigResponse:
    """Create an IDX feed configuration (requires active_agent/pro+ plan)."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    no_idx_plans = {"free", "lite", "starter"}
    if not tenant or tenant.plan in no_idx_plans:
        raise HTTPException(403, "IDX feed integration requires Active Agent plan or higher")

    # team/enterprise: unlimited. active_agent/pro: max 1.
    limited_plans = {"active_agent", "pro"}
    if tenant.plan in limited_plans:
        existing = await db.execute(
            select(func.count()).select_from(IdxFeedConfig).where(
                IdxFeedConfig.tenant_id == current_user.tenant_id
            )
        )
        if (existing.scalar() or 0) >= 1:
            raise HTTPException(409, "Your plan allows 1 IDX feed. Upgrade to Team for more.")

    config = IdxFeedConfig(
        tenant_id=current_user.tenant_id,
        name=body.name,
        base_url=body.base_url,
        api_key_encrypted=field_encryption.encrypt(body.api_key),
        board_id=body.board_id,
        poll_interval_minutes=body.poll_interval_minutes,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return IdxFeedConfigResponse.model_validate(config)


@router.get("/settings/idx-feed")
async def list_idx_feeds(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IdxFeedConfigResponse]:
    """List IDX feed configurations for the current tenant."""
    result = await db.execute(
        select(IdxFeedConfig).where(IdxFeedConfig.tenant_id == current_user.tenant_id)
    )
    return [IdxFeedConfigResponse.model_validate(c) for c in result.scalars().all()]


@router.patch("/settings/idx-feed/{config_id}")
async def update_idx_feed(
    config_id: uuid.UUID,
    body: IdxFeedConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IdxFeedConfigResponse:
    """Update an IDX feed configuration."""
    config = await db.get(IdxFeedConfig, config_id)
    if not config or config.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "IDX feed config not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "api_key" and value is not None:
            config.api_key_encrypted = field_encryption.encrypt(value)
        elif hasattr(config, field):
            setattr(config, field, value)

    await db.flush()
    await db.refresh(config)
    return IdxFeedConfigResponse.model_validate(config)


@router.delete("/settings/idx-feed/{config_id}", status_code=204)
async def delete_idx_feed(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an IDX feed configuration."""
    config = await db.get(IdxFeedConfig, config_id)
    if not config or config.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "IDX feed config not found")
    await db.delete(config)
    await db.flush()


# ---- Health Weights Endpoints ----


@router.get("/settings/health-weights")
async def get_health_weights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthWeightsResponse:
    """Get current health score weights for the tenant."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    plan = tenant.plan if tenant else "starter"
    weights = hs._resolve_weights(plan)
    return HealthWeightsResponse(
        media=weights.get("media", 0),
        content=weights.get("content", 0),
        velocity=weights.get("velocity", 0),
        syndication=weights.get("syndication", 0),
        market=weights.get("market", 0),
    )


@router.patch("/settings/health-weights")
async def update_health_weights(
    body: HealthWeightsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HealthWeightsResponse:
    """Customize health score weights (Enterprise only)."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant or tenant.plan not in ("team", "enterprise"):
        raise HTTPException(403, "Custom health weights require Enterprise plan")

    total = body.media + body.content + body.velocity + body.syndication + body.market
    if not (0.99 <= total <= 1.01):
        raise HTTPException(422, f"Weights must sum to 1.0 (got {total:.2f})")

    # TODO: persist custom weights in tenant metadata or dedicated table
    # For now, return the requested weights
    return HealthWeightsResponse(
        media=body.media,
        content=body.content,
        velocity=body.velocity,
        syndication=body.syndication,
        market=body.market,
    )
