"""
Outcome Tracker — links photo selections to listing sale outcomes via IDX data.

Responsibilities:
  1. ingest_outcome(): Called by IDX feed poller when a listing status changes
     to Pending or Closed. Creates/updates ListingOutcome with sale data.
  2. compute_correlations(): Aggregates across all closed listings for a tenant
     to find which photo attributes (room type, quality, position) correlate
     with better outcomes.  Results stored in PhotoOutcomeCorrelation.
  3. get_insights(): Returns human-readable insights for the tenant dashboard.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing_outcome import ListingOutcome
from listingjet.models.package_selection import PackageSelection
from listingjet.models.performance_event import PerformanceEvent
from listingjet.models.photo_outcome_correlation import PhotoOutcomeCorrelation
from listingjet.models.vision_result import VisionResult

logger = logging.getLogger(__name__)

# Grade thresholds based on days_on_market (lower = better)
GRADE_DOM_THRESHOLDS = {"A": 14, "B": 30, "C": 60, "D": 90}
# Grade numeric values for averaging
GRADE_VALUES = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}

# Minimum closed listings before correlations are meaningful
MIN_SAMPLE_SIZE = 3


def _compute_grade(days_on_market: int | None, price_ratio: float | None) -> str:
    """Compute a letter grade from DOM and sale-to-list price ratio."""
    score = 0.0
    factors = 0

    if days_on_market is not None:
        if days_on_market <= 14:
            score += 4.0
        elif days_on_market <= 30:
            score += 3.0
        elif days_on_market <= 60:
            score += 2.0
        elif days_on_market <= 90:
            score += 1.0
        factors += 1

    if price_ratio is not None:
        if price_ratio >= 1.0:
            score += 4.0  # Sold at or above list
        elif price_ratio >= 0.97:
            score += 3.0
        elif price_ratio >= 0.93:
            score += 2.0
        elif price_ratio >= 0.90:
            score += 1.0
        factors += 1

    if factors == 0:
        return "C"

    avg = score / factors
    if avg >= 3.5:
        return "A"
    if avg >= 2.5:
        return "B"
    if avg >= 1.5:
        return "C"
    if avg >= 0.5:
        return "D"
    return "F"


def _quality_bucket(score: float | None) -> str:
    """Bucket a 0-100 quality score into a label."""
    if score is None:
        return "unknown"
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _position_bucket(position: int | None) -> str:
    """Bucket a package position into a label."""
    if position is None:
        return "unknown"
    if position == 0:
        return "hero"
    if position <= 5:
        return "top_5"
    if position <= 12:
        return "mid"
    return "tail"


async def ingest_outcome(
    session: AsyncSession,
    listing_id: uuid.UUID,
    tenant_id: uuid.UUID,
    idx_data: dict,
    source: str = "idx",
) -> ListingOutcome:
    """Create or update a ListingOutcome from IDX feed data.

    Called by IdxFeedPoller when a listing status changes.
    """
    mls_status = idx_data.get("StandardStatus", "")
    status_map = {"Active": "active", "Pending": "pending", "Closed": "closed"}
    status = status_map.get(mls_status, mls_status.lower() if mls_status else "unknown")

    list_price = idx_data.get("ListPrice")
    sale_price = idx_data.get("ClosePrice") or idx_data.get("SoldPrice")
    dom = idx_data.get("DaysOnMarket")
    days_to_contract = idx_data.get("DaysToContract") or idx_data.get("CumulativeDaysOnMarket")

    price_ratio = None
    if sale_price and list_price and list_price > 0:
        price_ratio = sale_price / list_price

    # Count price changes from PerformanceEvents
    price_change_count = (await session.execute(
        select(func.count()).select_from(PerformanceEvent).where(
            PerformanceEvent.listing_id == listing_id,
            PerformanceEvent.signal_type == "idx.price_change",
        )
    )).scalar() or 0

    # Get photo package stats
    pkg_result = await session.execute(
        select(PackageSelection).where(
            PackageSelection.listing_id == listing_id,
            PackageSelection.channel == "mls",
        ).order_by(PackageSelection.position.asc())
    )
    selections = pkg_result.scalars().all()
    total_photos = len(selections)

    hero_room_label = None
    avg_score = None
    if selections:
        # Get hero room from vision results
        hero_sel = selections[0]
        vr_result = await session.execute(
            select(VisionResult).where(VisionResult.asset_id == hero_sel.asset_id).limit(1)
        )
        hero_vr = vr_result.scalar_one_or_none()
        if hero_vr:
            hero_room_label = hero_vr.room_label

        scores = [s.composite_score for s in selections if s.composite_score is not None]
        if scores:
            avg_score = sum(scores) / len(scores)

    grade = _compute_grade(dom, price_ratio)
    now = datetime.now(timezone.utc)

    values = {
        "tenant_id": tenant_id,
        "listing_id": listing_id,
        "status": status,
        "list_price": float(list_price) if list_price else None,
        "sale_price": float(sale_price) if sale_price else None,
        "price_ratio": price_ratio,
        "days_on_market": int(dom) if dom is not None else None,
        "days_to_contract": int(days_to_contract) if days_to_contract is not None else None,
        "price_changes": price_change_count,
        "total_photos_mls": total_photos,
        "hero_room_label": hero_room_label,
        "avg_photo_score": round(avg_score, 4) if avg_score else None,
        "outcome_grade": grade,
        "idx_source": source,
        "raw_idx_data": idx_data,
        "updated_at": now,
    }

    if status == "closed":
        values["closed_at"] = now

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
    return result.scalar_one()


async def compute_correlations(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> int:
    """Compute photo-outcome correlations across all closed listings for a tenant.

    Analyzes multiple dimensions:
    - room_label: which room types in the package correlate with better outcomes
    - hero_room: which room as hero photo correlates with better outcomes
    - quality_bucket: high/medium/low quality photos → outcomes
    - position_bucket: hero/top_5/mid/tail → outcome contribution

    Returns the number of correlation rows upserted.
    """
    # Get all closed outcomes for tenant
    outcomes_result = await session.execute(
        select(ListingOutcome).where(
            ListingOutcome.tenant_id == tenant_id,
            ListingOutcome.status == "closed",
        )
    )
    outcomes = outcomes_result.scalars().all()

    if len(outcomes) < MIN_SAMPLE_SIZE:
        logger.info(
            "outcome_tracker.skip_correlations tenant=%s closed=%d min=%d",
            tenant_id, len(outcomes), MIN_SAMPLE_SIZE,
        )
        return 0

    # Build lookup: listing_id → outcome
    outcome_map = {o.listing_id: o for o in outcomes}
    listing_ids = list(outcome_map.keys())

    # Load all package selections for these listings
    sel_result = await session.execute(
        select(PackageSelection).where(
            PackageSelection.listing_id.in_(listing_ids),
            PackageSelection.channel == "mls",
        )
    )
    all_selections = sel_result.scalars().all()

    # Load vision results for selected assets
    asset_ids = [s.asset_id for s in all_selections]
    if not asset_ids:
        return 0

    vr_result = await session.execute(
        select(VisionResult).where(VisionResult.asset_id.in_(asset_ids))
    )
    vr_map: dict[uuid.UUID, VisionResult] = {}
    for vr in vr_result.scalars().all():
        if vr.asset_id not in vr_map:
            vr_map[vr.asset_id] = vr

    # Aggregate by dimension
    # dimension → dimension_value → list of (dom, price_ratio, grade_val)
    aggregates: dict[str, dict[str, list[tuple[float | None, float | None, float]]]] = defaultdict(lambda: defaultdict(list))

    for sel in all_selections:
        outcome = outcome_map.get(sel.listing_id)
        if not outcome:
            continue

        grade_val = GRADE_VALUES.get(outcome.outcome_grade or "C", 2.0)
        data_point = (
            float(outcome.days_on_market) if outcome.days_on_market is not None else None,
            outcome.price_ratio,
            grade_val,
        )

        vr = vr_map.get(sel.asset_id)
        room = vr.room_label if vr else "unknown"

        # Dimension: room_label
        aggregates["room_label"][room].append(data_point)

        # Dimension: hero_room (only for position 0)
        if sel.position == 0:
            aggregates["hero_room"][room].append(data_point)

        # Dimension: quality_bucket
        quality = vr.quality_score if vr else None
        bucket = _quality_bucket(quality)
        aggregates["quality_bucket"][bucket].append(data_point)

        # Dimension: position_bucket
        pos_bucket = _position_bucket(sel.position)
        aggregates["position_bucket"][pos_bucket].append(data_point)

    # Compute averages and outcome_boost
    now = datetime.now(timezone.utc)

    # Get global averages for boost calculation
    all_doms = [float(o.days_on_market) for o in outcomes if o.days_on_market is not None]
    global_avg_dom = sum(all_doms) / len(all_doms) if all_doms else 30.0
    all_ratios = [o.price_ratio for o in outcomes if o.price_ratio is not None]
    global_avg_ratio = sum(all_ratios) / len(all_ratios) if all_ratios else 1.0

    upserted = 0
    for dimension, values_by_key in aggregates.items():
        for dim_value, data_points in values_by_key.items():
            if len(data_points) < 1:
                continue

            doms = [d[0] for d in data_points if d[0] is not None]
            ratios = [d[1] for d in data_points if d[1] is not None]
            grades = [d[2] for d in data_points]

            avg_dom = sum(doms) / len(doms) if doms else None
            avg_ratio = sum(ratios) / len(ratios) if ratios else None
            avg_grade = sum(grades) / len(grades) if grades else None

            # Compute outcome_boost: how this dimension value compares to global average
            # boost > 1.0 = better than average, < 1.0 = worse
            boost = 1.0
            boost_factors = 0
            if avg_dom is not None and global_avg_dom > 0:
                # Lower DOM is better → invert ratio
                dom_boost = global_avg_dom / max(avg_dom, 1.0)
                boost += (dom_boost - 1.0)
                boost_factors += 1
            if avg_ratio is not None and global_avg_ratio > 0:
                ratio_boost = avg_ratio / global_avg_ratio
                boost += (ratio_boost - 1.0)
                boost_factors += 1

            if boost_factors > 0:
                # Average the boost contributions, then clamp
                boost = 1.0 + (boost - 1.0) / boost_factors
            boost = max(0.5, min(1.5, boost))

            row_values = {
                "tenant_id": tenant_id,
                "dimension": dimension,
                "dimension_value": dim_value,
                "sample_count": len(data_points),
                "avg_dom": round(avg_dom, 1) if avg_dom is not None else None,
                "avg_price_ratio": round(avg_ratio, 4) if avg_ratio is not None else None,
                "avg_outcome_grade": round(avg_grade, 2) if avg_grade is not None else None,
                "outcome_boost": round(boost, 4),
                "calculated_at": now,
            }

            stmt = pg_insert(PhotoOutcomeCorrelation).values(id=uuid.uuid4(), **row_values)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_poc_tenant_dim_val",
                set_={k: v for k, v in row_values.items() if k not in ("tenant_id", "dimension", "dimension_value")},
            )
            await session.execute(stmt)
            upserted += 1

    await session.flush()
    logger.info(
        "outcome_tracker.correlations_computed tenant=%s outcomes=%d correlations=%d",
        tenant_id, len(outcomes), upserted,
    )
    return upserted


async def get_outcome_boost(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    room_label: str,
) -> float:
    """Get the outcome-based boost factor for a room label.

    Used by WeightManager to incorporate real sale performance
    into photo scoring.
    """
    result = await session.execute(
        select(PhotoOutcomeCorrelation.outcome_boost).where(
            PhotoOutcomeCorrelation.tenant_id == tenant_id,
            PhotoOutcomeCorrelation.dimension == "room_label",
            PhotoOutcomeCorrelation.dimension_value == room_label,
        )
    )
    boost = result.scalar_one_or_none()
    return boost if boost is not None else 1.0


async def get_insights(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> dict:
    """Generate human-readable performance insights for a tenant.

    Returns:
        dict with keys: summary, top_rooms, hero_insights, quality_impact,
                        outcomes_count, avg_dom, avg_price_ratio
    """
    # Get outcome summary
    outcomes_result = await session.execute(
        select(ListingOutcome).where(
            ListingOutcome.tenant_id == tenant_id,
            ListingOutcome.status == "closed",
        )
    )
    outcomes = outcomes_result.scalars().all()

    total_outcomes = len(outcomes)
    if total_outcomes == 0:
        return {
            "summary": "No closed listings yet. Outcomes will appear as listings sell.",
            "outcomes_count": 0,
            "top_rooms": [],
            "hero_insights": [],
            "quality_impact": [],
            "avg_dom": None,
            "avg_price_ratio": None,
            "grade_distribution": {},
        }

    avg_dom_vals = [o.days_on_market for o in outcomes if o.days_on_market is not None]
    avg_dom = round(sum(avg_dom_vals) / len(avg_dom_vals), 1) if avg_dom_vals else None
    avg_ratio_vals = [o.price_ratio for o in outcomes if o.price_ratio is not None]
    avg_price_ratio = round(sum(avg_ratio_vals) / len(avg_ratio_vals), 4) if avg_ratio_vals else None

    grade_dist: dict[str, int] = {}
    for o in outcomes:
        g = o.outcome_grade or "C"
        grade_dist[g] = grade_dist.get(g, 0) + 1

    # Load correlations
    corr_result = await session.execute(
        select(PhotoOutcomeCorrelation).where(
            PhotoOutcomeCorrelation.tenant_id == tenant_id,
        ).order_by(PhotoOutcomeCorrelation.outcome_boost.desc())
    )
    correlations = corr_result.scalars().all()

    # Group by dimension
    by_dim: dict[str, list[PhotoOutcomeCorrelation]] = defaultdict(list)
    for c in correlations:
        by_dim[c.dimension].append(c)

    # Top rooms (by outcome boost)
    room_corrs = sorted(
        by_dim.get("room_label", []),
        key=lambda c: c.outcome_boost, reverse=True,
    )
    top_rooms = [
        {
            "room": c.dimension_value,
            "boost": round(c.outcome_boost, 2),
            "avg_dom": c.avg_dom,
            "sample_count": c.sample_count,
        }
        for c in room_corrs[:5]
    ]

    # Hero insights
    hero_corrs = sorted(
        by_dim.get("hero_room", []),
        key=lambda c: c.outcome_boost, reverse=True,
    )
    hero_insights = [
        {
            "room": c.dimension_value,
            "boost": round(c.outcome_boost, 2),
            "avg_dom": c.avg_dom,
            "avg_price_ratio": c.avg_price_ratio,
            "sample_count": c.sample_count,
        }
        for c in hero_corrs
    ]

    # Quality impact
    quality_corrs = sorted(
        by_dim.get("quality_bucket", []),
        key=lambda c: c.outcome_boost, reverse=True,
    )
    quality_impact = [
        {
            "bucket": c.dimension_value,
            "boost": round(c.outcome_boost, 2),
            "avg_dom": c.avg_dom,
            "sample_count": c.sample_count,
        }
        for c in quality_corrs
    ]

    # Generate summary text
    summary_parts = [f"Based on {total_outcomes} closed listing(s)."]
    if avg_dom is not None:
        summary_parts.append(f"Average days on market: {avg_dom}.")
    if avg_price_ratio is not None:
        pct = round((avg_price_ratio - 1.0) * 100, 1)
        if pct >= 0:
            summary_parts.append(f"Average sale price {pct}% above list.")
        else:
            summary_parts.append(f"Average sale price {abs(pct)}% below list.")
    if top_rooms and top_rooms[0]["boost"] > 1.05:
        summary_parts.append(
            f"Listings with strong {top_rooms[0]['room']} photos perform best."
        )

    return {
        "summary": " ".join(summary_parts),
        "outcomes_count": total_outcomes,
        "avg_dom": avg_dom,
        "avg_price_ratio": avg_price_ratio,
        "grade_distribution": grade_dist,
        "top_rooms": top_rooms,
        "hero_insights": hero_insights,
        "quality_impact": quality_impact,
    }
