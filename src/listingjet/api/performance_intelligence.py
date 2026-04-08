"""
Performance Intelligence API — photo-to-outcome insights.

Endpoints:
  GET  /analytics/performance       — tenant-wide outcome insights & correlations
  GET  /analytics/performance/outcomes — listing outcome summary with pagination
  GET  /listings/{listing_id}/outcome — single listing outcome details
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.api.schemas.performance import (
    HeroInsight,
    ListingOutcomeResponse,
    OutcomeSummaryResponse,
    PerformanceInsightsResponse,
    QualityImpact,
    RoomCorrelation,
)
from listingjet.models.listing_outcome import ListingOutcome
from listingjet.models.user import User
from listingjet.services.outcome_tracker import get_insights

router = APIRouter()


@router.get("/analytics/performance")
async def performance_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PerformanceInsightsResponse:
    """Tenant-wide performance intelligence: photo-to-outcome correlations."""
    raw = await get_insights(db, current_user.tenant_id)
    return PerformanceInsightsResponse(
        summary=raw["summary"],
        outcomes_count=raw["outcomes_count"],
        avg_dom=raw.get("avg_dom"),
        avg_price_ratio=raw.get("avg_price_ratio"),
        grade_distribution=raw.get("grade_distribution", {}),
        top_rooms=[RoomCorrelation(**r) for r in raw.get("top_rooms", [])],
        hero_insights=[HeroInsight(**h) for h in raw.get("hero_insights", [])],
        quality_impact=[QualityImpact(**q) for q in raw.get("quality_impact", [])],
    )


@router.get("/analytics/performance/outcomes")
async def list_outcomes(
    status: str | None = Query(None, pattern="^(active|pending|closed)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OutcomeSummaryResponse:
    """Paginated list of listing outcomes with summary stats."""
    tid = current_user.tenant_id

    base = select(ListingOutcome).where(ListingOutcome.tenant_id == tid)
    if status:
        base = base.where(ListingOutcome.status == status)

    # Summary stats
    all_result = await db.execute(
        select(ListingOutcome).where(ListingOutcome.tenant_id == tid)
    )
    all_outcomes = all_result.scalars().all()
    total_tracked = len(all_outcomes)
    total_closed = sum(1 for o in all_outcomes if o.status == "closed")
    total_pending = sum(1 for o in all_outcomes if o.status == "pending")
    total_active = sum(1 for o in all_outcomes if o.status == "active")

    doms = [o.days_on_market for o in all_outcomes if o.days_on_market is not None and o.status == "closed"]
    avg_dom = round(sum(doms) / len(doms), 1) if doms else None
    ratios = [o.price_ratio for o in all_outcomes if o.price_ratio is not None and o.status == "closed"]
    avg_ratio = round(sum(ratios) / len(ratios), 4) if ratios else None

    grade_dist: dict[str, int] = {}
    for o in all_outcomes:
        if o.status == "closed" and o.outcome_grade:
            grade_dist[o.outcome_grade] = grade_dist.get(o.outcome_grade, 0) + 1

    # Paginated listing
    result = await db.execute(
        base.order_by(ListingOutcome.updated_at.desc()).offset(offset).limit(limit)
    )
    rows = result.scalars().all()

    return OutcomeSummaryResponse(
        total_tracked=total_tracked,
        total_closed=total_closed,
        total_pending=total_pending,
        total_active=total_active,
        avg_dom=avg_dom,
        avg_price_ratio=avg_ratio,
        grade_distribution=grade_dist,
        listings=[ListingOutcomeResponse.model_validate(r) for r in rows],
    )


@router.get("/listings/{listing_id}/outcome")
async def get_listing_outcome(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListingOutcomeResponse:
    """Get the outcome data for a single listing."""
    result = await db.execute(
        select(ListingOutcome).where(
            ListingOutcome.listing_id == listing_id,
            ListingOutcome.tenant_id == current_user.tenant_id,
        )
    )
    outcome = result.scalar_one_or_none()
    if not outcome:
        raise HTTPException(404, "No outcome data for this listing")
    return ListingOutcomeResponse.model_validate(outcome)
