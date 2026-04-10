"""Performance Intelligence — correlate photo selections with listing outcomes.

Materializes listing_outcomes from IDX + pipeline data, then computes
tenant-level insights and platform-wide marketing claims.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing, ListingState
from listingjet.models.listing_health_score import ListingHealthScore
from listingjet.models.listing_outcome import ListingOutcome
from listingjet.models.package_selection import PackageSelection
from listingjet.models.performance_event import PerformanceEvent
from listingjet.models.performance_insight import PerformanceInsight
from listingjet.models.vision_result import VisionResult

logger = logging.getLogger(__name__)

REQUIRED_SHOTS = {"exterior", "living_room", "kitchen", "bedroom", "bathroom"}
MIN_SAMPLE_SIZE = 5  # Minimum listings for meaningful correlations


async def materialize_outcome(
    session: AsyncSession, listing_id: uuid.UUID, tenant_id: uuid.UUID
) -> ListingOutcome | None:
    """Build/update a listing_outcomes row from pipeline + IDX data."""
    listing = await session.get(Listing, listing_id)
    if not listing or listing.state != ListingState.DELIVERED:
        return None

    # Photo metrics from VisionResult + PackageSelection
    pkg_result = await session.execute(
        select(PackageSelection).where(PackageSelection.listing_id == listing_id)
    )
    selections = pkg_result.scalars().all()
    photo_count = len(selections)

    # Get vision results for selected photos
    asset_ids = [s.asset_id for s in selections]
    quality_scores = []
    commercial_scores = []
    room_labels = set()
    hero_quality = None

    if asset_ids:
        vr_result = await session.execute(
            select(VisionResult).where(
                VisionResult.asset_id.in_(asset_ids),
                VisionResult.tier == 1,
            )
        )
        for vr in vr_result.scalars().all():
            if vr.quality_score is not None:
                quality_scores.append(vr.quality_score)
            if vr.commercial_score is not None:
                commercial_scores.append(vr.commercial_score)
            if vr.room_label:
                room_labels.add(vr.room_label)
            if vr.hero_candidate and vr.quality_score is not None:
                hero_quality = max(hero_quality or 0, vr.quality_score)

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    avg_commercial = sum(commercial_scores) / len(commercial_scores) if commercial_scores else None
    coverage = len(room_labels & REQUIRED_SHOTS) / len(REQUIRED_SHOTS) * 100

    # Override rate
    overrides = sum(1 for s in selections if s.selected_by != "ai")
    override_rate = overrides / max(photo_count, 1)

    # Health score at delivery
    hs_result = await session.execute(
        select(ListingHealthScore).where(ListingHealthScore.listing_id == listing_id)
    )
    health_score = hs_result.scalar_one_or_none()
    health_at_delivery = health_score.overall_score if health_score else None

    # IDX outcome data from PerformanceEvents
    idx_result = await session.execute(
        select(PerformanceEvent).where(
            PerformanceEvent.listing_id == listing_id,
            PerformanceEvent.signal_type.like("idx.%"),
        ).order_by(PerformanceEvent.recorded_at.desc())
    )
    idx_events = idx_result.scalars().all()

    dom = None
    status = "active"
    price_changes = 0
    final_price = None
    original_price = None

    for e in idx_events:
        if e.signal_type == "idx.dom_update" and dom is None:
            dom = int(e.value) if e.value else None
        elif e.signal_type == "idx.status_change":
            val = e.value
            if val == 1.0:
                status = "active"
            elif val == 2.0:
                status = "pending"
            elif val == 3.0:
                status = "sold"
        elif e.signal_type == "idx.price_change":
            price_changes += 1
            if final_price is None:
                final_price = e.value
            original_price = e.value  # Last one chronologically is the original

    # Upsert
    values = {
        "tenant_id": tenant_id,
        "listing_id": listing_id,
        "days_on_market": dom,
        "final_price": final_price,
        "original_price": original_price,
        "price_change_count": price_changes,
        "status": status,
        "avg_photo_quality": round(avg_quality, 1) if avg_quality else None,
        "avg_commercial_score": round(avg_commercial, 1) if avg_commercial else None,
        "hero_quality": hero_quality,
        "coverage_pct": round(coverage, 1),
        "photo_count": photo_count,
        "room_diversity": len(room_labels),
        "override_rate": round(override_rate, 3),
        "health_score_at_delivery": health_at_delivery,
        "updated_at": datetime.now(timezone.utc),
    }

    stmt = pg_insert(ListingOutcome).values(id=uuid.uuid4(), **values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["listing_id"],
        set_={k: v for k, v in values.items() if k != "listing_id"},
    )
    await session.execute(stmt)
    await session.flush()

    result = await session.execute(
        select(ListingOutcome).where(ListingOutcome.listing_id == listing_id)
    )
    return result.scalar_one_or_none()


async def compute_tenant_insights(
    session: AsyncSession, tenant_id: uuid.UUID
) -> list[dict]:
    """Compute performance insights for a tenant from their listing_outcomes."""
    result = await session.execute(
        select(ListingOutcome).where(ListingOutcome.tenant_id == tenant_id)
    )
    outcomes = result.scalars().all()
    now = datetime.now(timezone.utc)

    if len(outcomes) < MIN_SAMPLE_SIZE:
        return []

    insights = []

    # 1. DOM summary
    dom_values = [o.days_on_market for o in outcomes if o.days_on_market is not None]
    if dom_values:
        avg_dom = sum(dom_values) / len(dom_values)
        insights.append({
            "type": "dom_summary",
            "data": {
                "avg_dom": round(avg_dom, 1),
                "min_dom": min(dom_values),
                "max_dom": max(dom_values),
                "sold_count": sum(1 for o in outcomes if o.status == "sold"),
                "total": len(outcomes),
            },
            "sample_size": len(dom_values),
        })

    # 2. Quality → DOM correlation
    quality_dom_pairs = [
        (o.avg_photo_quality, o.days_on_market)
        for o in outcomes
        if o.avg_photo_quality is not None and o.days_on_market is not None
    ]
    if len(quality_dom_pairs) >= MIN_SAMPLE_SIZE:
        high_quality = [dom for q, dom in quality_dom_pairs if q >= 75]
        low_quality = [dom for q, dom in quality_dom_pairs if q < 75]
        if high_quality and low_quality:
            hq_avg = sum(high_quality) / len(high_quality)
            lq_avg = sum(low_quality) / len(low_quality)
            diff_days = round(lq_avg - hq_avg, 1)
            diff_pct = round((lq_avg - hq_avg) / max(lq_avg, 1) * 100, 1)
            insights.append({
                "type": "quality_dom_correlation",
                "data": {
                    "high_quality_avg_dom": round(hq_avg, 1),
                    "low_quality_avg_dom": round(lq_avg, 1),
                    "difference_days": diff_days,
                    "difference_pct": diff_pct,
                    "high_quality_count": len(high_quality),
                    "low_quality_count": len(low_quality),
                },
                "sample_size": len(quality_dom_pairs),
            })

    # 3. Hero photo impact
    hero_dom_pairs = [
        (o.hero_quality, o.days_on_market)
        for o in outcomes
        if o.hero_quality is not None and o.days_on_market is not None
    ]
    if len(hero_dom_pairs) >= MIN_SAMPLE_SIZE:
        strong_hero = [dom for h, dom in hero_dom_pairs if h >= 80]
        weak_hero = [dom for h, dom in hero_dom_pairs if h < 80]
        if strong_hero and weak_hero:
            insights.append({
                "type": "hero_impact",
                "data": {
                    "strong_hero_avg_dom": round(sum(strong_hero) / len(strong_hero), 1),
                    "weak_hero_avg_dom": round(sum(weak_hero) / len(weak_hero), 1),
                    "strong_count": len(strong_hero),
                    "weak_count": len(weak_hero),
                },
                "sample_size": len(hero_dom_pairs),
            })

    # 4. Coverage impact
    coverage_dom_pairs = [
        (o.coverage_pct, o.days_on_market)
        for o in outcomes
        if o.coverage_pct is not None and o.days_on_market is not None
    ]
    if len(coverage_dom_pairs) >= MIN_SAMPLE_SIZE:
        full_cov = [dom for c, dom in coverage_dom_pairs if c >= 100]
        partial_cov = [dom for c, dom in coverage_dom_pairs if c < 100]
        if full_cov and partial_cov:
            insights.append({
                "type": "coverage_impact",
                "data": {
                    "full_coverage_avg_dom": round(sum(full_cov) / len(full_cov), 1),
                    "partial_coverage_avg_dom": round(sum(partial_cov) / len(partial_cov), 1),
                    "full_count": len(full_cov),
                    "partial_count": len(partial_cov),
                },
                "sample_size": len(coverage_dom_pairs),
            })

    # 5. Override rate impact
    override_dom_pairs = [
        (o.override_rate, o.days_on_market)
        for o in outcomes
        if o.override_rate is not None and o.days_on_market is not None
    ]
    if len(override_dom_pairs) >= MIN_SAMPLE_SIZE:
        low_override = [dom for r, dom in override_dom_pairs if r <= 0.1]
        high_override = [dom for r, dom in override_dom_pairs if r > 0.1]
        if low_override and high_override:
            insights.append({
                "type": "override_impact",
                "data": {
                    "trusted_ai_avg_dom": round(sum(low_override) / len(low_override), 1),
                    "high_override_avg_dom": round(sum(high_override) / len(high_override), 1),
                    "trusted_count": len(low_override),
                    "override_count": len(high_override),
                },
                "sample_size": len(override_dom_pairs),
            })

    # Persist insights
    for insight in insights:
        session.add(PerformanceInsight(
            tenant_id=tenant_id,
            insight_type=insight["type"],
            data=insight["data"],
            sample_size=insight["sample_size"],
            calculated_at=now,
        ))
    await session.flush()

    return insights


async def get_listing_insight(
    session: AsyncSession, listing_id: uuid.UUID, tenant_id: uuid.UUID
) -> dict | None:
    """Get performance insight card for a specific listing."""
    outcome = await session.execute(
        select(ListingOutcome).where(ListingOutcome.listing_id == listing_id)
    )
    listing_outcome = outcome.scalar_one_or_none()
    if not listing_outcome:
        return None

    # Compare to tenant averages
    avg_result = await session.execute(
        select(
            func.avg(ListingOutcome.days_on_market).label("avg_dom"),
            func.avg(ListingOutcome.avg_photo_quality).label("avg_quality"),
            func.count().label("total"),
        ).where(ListingOutcome.tenant_id == tenant_id)
    )
    avgs = avg_result.one()

    comparisons = {}
    if listing_outcome.days_on_market is not None and avgs.avg_dom:
        diff = round(float(avgs.avg_dom) - listing_outcome.days_on_market, 1)
        comparisons["dom_vs_avg"] = {
            "listing_dom": listing_outcome.days_on_market,
            "tenant_avg_dom": round(float(avgs.avg_dom), 1),
            "difference": diff,
            "better": diff > 0,
        }

    if listing_outcome.avg_photo_quality is not None and avgs.avg_quality:
        diff = round(listing_outcome.avg_photo_quality - float(avgs.avg_quality), 1)
        comparisons["quality_vs_avg"] = {
            "listing_quality": listing_outcome.avg_photo_quality,
            "tenant_avg_quality": round(float(avgs.avg_quality), 1),
            "difference": diff,
            "better": diff > 0,
        }

    return {
        "listing_id": str(listing_id),
        "outcome": {
            "days_on_market": listing_outcome.days_on_market,
            "status": listing_outcome.status,
            "price_changes": listing_outcome.price_change_count,
            "photo_count": listing_outcome.photo_count,
            "avg_quality": listing_outcome.avg_photo_quality,
            "hero_quality": listing_outcome.hero_quality,
            "coverage_pct": listing_outcome.coverage_pct,
            "override_rate": listing_outcome.override_rate,
            "health_score": listing_outcome.health_score_at_delivery,
        },
        "comparisons": comparisons,
        "sample_size": avgs.total or 0,
    }


async def compute_platform_claims(session: AsyncSession) -> dict:
    """Compute platform-wide marketing claims from all listing outcomes (admin only)."""
    result = await session.execute(select(ListingOutcome))
    all_outcomes = result.scalars().all()

    if len(all_outcomes) < MIN_SAMPLE_SIZE * 2:
        return {"claims": [], "sample_size": len(all_outcomes), "sufficient_data": False}

    dom_values = [o.days_on_market for o in all_outcomes if o.days_on_market is not None]
    quality_values = [o.avg_photo_quality for o in all_outcomes if o.avg_photo_quality is not None]
    sold_count = sum(1 for o in all_outcomes if o.status == "sold")

    claims = []

    if dom_values:
        avg_dom = sum(dom_values) / len(dom_values)
        claims.append({
            "claim": f"LaunchLens listings average {round(avg_dom)} days on market",
            "metric": "avg_dom",
            "value": round(avg_dom, 1),
            "sample_size": len(dom_values),
        })

    if quality_values:
        avg_q = sum(quality_values) / len(quality_values)
        claims.append({
            "claim": f"Average photo quality score: {round(avg_q)}/100",
            "metric": "avg_quality",
            "value": round(avg_q, 1),
            "sample_size": len(quality_values),
        })

    if sold_count:
        sell_rate = round(sold_count / len(all_outcomes) * 100, 1)
        claims.append({
            "claim": f"{sell_rate}% of LaunchLens listings have sold",
            "metric": "sell_through_rate",
            "value": sell_rate,
            "sample_size": len(all_outcomes),
        })

    return {
        "claims": claims,
        "sample_size": len(all_outcomes),
        "sufficient_data": True,
    }
