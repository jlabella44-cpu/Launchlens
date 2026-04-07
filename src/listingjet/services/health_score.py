"""
Listing Health Score service — composite 0-100 score from automated signals.

Sub-scores:
  - Media Quality (30%): photo quality, commercial appeal, hero strength, coverage
  - Content Readiness (20%): description, FHA, social, flyer, export bundles
  - Pipeline Velocity (15%): elapsed time, review turnaround, override rate, failures
  - Syndication Status (20%): IDX presence, photo match, listing status, DOM
  - Market Signal (15%): price stability, DOM vs median, status progression
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.health_score_history import HealthScoreHistory
from listingjet.models.listing import Listing, ListingState
from listingjet.models.listing_health_score import ListingHealthScore
from listingjet.models.package_selection import PackageSelection
from listingjet.models.performance_event import PerformanceEvent
from listingjet.models.social_content import SocialContent
from listingjet.models.vision_result import VisionResult

logger = logging.getLogger(__name__)

# Required shots from CoverageAgent
REQUIRED_SHOTS = {"exterior", "living_room", "kitchen", "bedroom", "bathroom"}

# Default weights by plan tier — unavailable sub-scores get redistributed
DEFAULT_WEIGHTS = {
    "media": 0.30,
    "content": 0.20,
    "velocity": 0.15,
    "syndication": 0.20,
    "market": 0.15,
}

# Which sub-scores are available per plan
PLAN_SUBSCORES = {
    # New pricing tiers
    "free": {"media", "content"},
    "lite": {"media", "content"},
    "active_agent": {"media", "content", "velocity", "syndication"},
    "team": {"media", "content", "velocity", "syndication", "market"},
    # Legacy aliases
    "starter": {"media", "content"},
    "pro": {"media", "content", "velocity", "syndication"},
    "enterprise": {"media", "content", "velocity", "syndication", "market"},
}


def _resolve_weights(plan: str, custom_weights: dict | None = None) -> dict[str, float]:
    """Resolve effective weights: custom (enterprise) → plan defaults → redistribute."""
    if custom_weights and plan == "enterprise":
        # Validate custom weights sum to ~1.0
        total = sum(custom_weights.values())
        if 0.99 <= total <= 1.01:
            return custom_weights

    available = PLAN_SUBSCORES.get(plan, PLAN_SUBSCORES["starter"])
    raw = {k: v for k, v in DEFAULT_WEIGHTS.items() if k in available}
    # Redistribute unavailable weight proportionally
    total = sum(raw.values())
    if total == 0:
        return {k: 1.0 / len(raw) for k in raw} if raw else {}
    return {k: v / total for k, v in raw.items()}


def _clamp(value: float) -> int:
    return min(100, max(0, int(value)))


async def calculate_media_score(session: AsyncSession, listing_id: uuid.UUID) -> tuple[int, dict]:
    """Media Quality sub-score from VisionResult + PackageSelection.

    This replaces and extends the old predict_engagement() heuristic.
    """
    # Get vision results for this listing's assets
    result = await session.execute(
        select(VisionResult)
        .join(Asset, VisionResult.asset_id == Asset.id)
        .where(Asset.listing_id == listing_id, VisionResult.tier == 1)
    )
    vision_results = result.scalars().all()

    if not vision_results:
        return 50, {"avg_quality": 0, "avg_commercial": 0, "hero_strength": 0, "coverage_pct": 0}

    avg_quality = sum(vr.quality_score or 50 for vr in vision_results) / len(vision_results)
    avg_commercial = sum(vr.commercial_score or 50 for vr in vision_results) / len(vision_results)

    # Hero strength: best hero candidate's commercial score
    hero_results = [vr for vr in vision_results if vr.hero_candidate]
    hero_strength = max((vr.commercial_score or 0 for vr in hero_results), default=0) if hero_results else 0

    # Coverage: % of required shots present
    covered = {vr.room_label for vr in vision_results if vr.room_label}
    coverage_pct = len(covered & REQUIRED_SHOTS) / len(REQUIRED_SHOTS) * 100

    # Weighted: 40% quality + 30% commercial + 15% hero + 15% coverage
    score = avg_quality * 0.40 + avg_commercial * 0.30 + hero_strength * 0.15 + coverage_pct * 0.15

    details = {
        "avg_quality": round(avg_quality, 1),
        "avg_commercial": round(avg_commercial, 1),
        "hero_strength": hero_strength,
        "coverage_pct": round(coverage_pct, 1),
    }
    return _clamp(score), details


async def calculate_content_score(
    session: AsyncSession, listing_id: uuid.UUID, tenant_id: uuid.UUID
) -> tuple[int, dict]:
    """Content Readiness sub-score from pipeline outputs."""
    listing = await session.get(Listing, listing_id)
    if not listing:
        return 0, {}

    # Check what content has been generated
    has_description = listing.state.value in (
        "approved", "exporting", "delivered",
    )

    has_mls_bundle = bool(listing.mls_bundle_path)
    has_marketing_bundle = bool(listing.marketing_bundle_path)

    # Social content
    social_result = await session.execute(
        select(func.count()).select_from(SocialContent).where(
            SocialContent.listing_id == listing_id
        )
    )
    social_count = social_result.scalar() or 0
    has_social = social_count > 0

    # Brand kit configured for tenant
    brand_result = await session.execute(
        select(BrandKit).where(BrandKit.tenant_id == tenant_id).limit(1)
    )
    brand_kit = brand_result.scalar_one_or_none()
    has_brand = bool(brand_kit and brand_kit.logo_url and brand_kit.primary_color)

    # FHA: check for compliance events (absence = passed)
    fha_result = await session.execute(
        select(func.count()).select_from(PerformanceEvent).where(
            PerformanceEvent.listing_id == listing_id,
            PerformanceEvent.signal_type == "fha_violation",
        )
    )
    fha_violations = fha_result.scalar() or 0
    fha_passed = fha_violations == 0

    # Score: each component worth 20 points
    score = 0
    if has_description:
        score += 20
    if fha_passed:
        score += 20
    if has_social:
        score += 20
    if has_brand:
        score += 20
    if has_mls_bundle or has_marketing_bundle:
        score += 20

    details = {
        "description": has_description,
        "fha_passed": fha_passed,
        "social": has_social,
        "brand_kit": has_brand,
        "export": has_mls_bundle or has_marketing_bundle,
    }
    return _clamp(score), details


async def calculate_velocity_score(
    session: AsyncSession, listing_id: uuid.UUID, tenant_id: uuid.UUID
) -> tuple[int, dict]:
    """Pipeline Velocity sub-score from timing and override signals."""
    # Get performance events for this listing
    result = await session.execute(
        select(PerformanceEvent).where(
            PerformanceEvent.listing_id == listing_id,
        )
    )
    events = result.scalars().all()
    events_by_type = {}
    for e in events:
        events_by_type.setdefault(e.signal_type, []).append(e)

    score = 100  # Start at 100, deduct for issues
    details: dict = {"elapsed_minutes": None, "review_minutes": None, "override_rate": 0.0, "failures": 0}

    # Elapsed time: upload → delivered
    listing = await session.get(Listing, listing_id)
    if listing and listing.state == ListingState.DELIVERED:
        elapsed = (listing.updated_at - listing.created_at).total_seconds() / 60.0
        details["elapsed_minutes"] = round(elapsed, 1)
        # Penalize slow pipelines: >30 min loses points
        if elapsed > 60:
            score -= 30
        elif elapsed > 30:
            score -= 15
        elif elapsed > 10:
            score -= 5

    # Review turnaround
    review_events = events_by_type.get("review_turnaround", [])
    if review_events:
        review_min = review_events[-1].value or 0
        details["review_minutes"] = round(review_min, 1)
        if review_min > 120:  # 2+ hours
            score -= 20
        elif review_min > 30:
            score -= 10

    # Override rate: high overrides = AI not trusted
    override_events = events_by_type.get("listing.override", [])
    total_selections_result = await session.execute(
        select(func.count()).select_from(PackageSelection).where(
            PackageSelection.listing_id == listing_id
        )
    )
    total_selections = total_selections_result.scalar() or 1
    override_rate = len(override_events) / max(total_selections, 1)
    details["override_rate"] = round(override_rate, 3)
    if override_rate > 0.3:
        score -= 20
    elif override_rate > 0.1:
        score -= 10

    # Failures
    failure_events = events_by_type.get("pipeline.failed", [])
    details["failures"] = len(failure_events)
    score -= len(failure_events) * 15

    return _clamp(score), details


async def calculate_syndication_score(
    session: AsyncSession, listing_id: uuid.UUID
) -> tuple[int, dict]:
    """Syndication Status sub-score from IDX feed signals."""
    result = await session.execute(
        select(PerformanceEvent).where(
            PerformanceEvent.listing_id == listing_id,
            PerformanceEvent.signal_type.like("idx.%"),
        ).order_by(PerformanceEvent.recorded_at.desc())
    )
    idx_events = result.scalars().all()

    if not idx_events:
        # No IDX data yet — neutral score
        return 50, {"idx_active": None, "photo_match": None, "photo_expected": None, "dom": None}

    latest_by_type: dict[str, PerformanceEvent] = {}
    for e in idx_events:
        if e.signal_type not in latest_by_type:
            latest_by_type[e.signal_type] = e

    score = 0
    details: dict = {"idx_active": None, "photo_match": None, "photo_expected": None, "dom": None}

    # IDX active status
    status_event = latest_by_type.get("idx.status_change")
    if status_event:
        idx_active = status_event.value == 1.0  # 1.0 = active
        details["idx_active"] = idx_active
        score += 30 if idx_active else 0

    # Photo count match
    photo_event = latest_by_type.get("idx.photo_count")
    if photo_event:
        # Get expected photo count from package selections
        expected_result = await session.execute(
            select(func.count()).select_from(PackageSelection).where(
                PackageSelection.listing_id == listing_id
            )
        )
        expected = expected_result.scalar() or 0
        actual = int(photo_event.value or 0)
        details["photo_match"] = actual
        details["photo_expected"] = expected
        if expected > 0:
            match_ratio = min(actual / expected, 1.0)
            score += int(30 * match_ratio)

    # Days on market
    dom_event = latest_by_type.get("idx.dom_update")
    if dom_event:
        dom = int(dom_event.value or 0)
        details["dom"] = dom
        # Lower DOM = better. 0-14 days = full points, 90+ = 0
        if dom <= 14:
            score += 40
        elif dom <= 30:
            score += 30
        elif dom <= 60:
            score += 20
        elif dom <= 90:
            score += 10

    # If we had some events but not all, scale up proportionally
    if not status_event and not photo_event and not dom_event:
        return 50, details

    return _clamp(score), details


async def calculate_market_score(
    session: AsyncSession, listing_id: uuid.UUID
) -> tuple[int, dict]:
    """Market Signal sub-score from RESO performance data."""
    result = await session.execute(
        select(PerformanceEvent).where(
            PerformanceEvent.listing_id == listing_id,
            PerformanceEvent.signal_type.like("idx.%"),
        ).order_by(PerformanceEvent.recorded_at.desc())
    )
    idx_events = result.scalars().all()

    details: dict = {"price_changes": 0, "dom_vs_median": None, "status": None}

    if not idx_events:
        return 50, details

    score = 100

    # Price changes: count idx.price_change events — fewer = more stable
    price_changes = [e for e in idx_events if e.signal_type == "idx.price_change"]
    details["price_changes"] = len(price_changes)
    score -= len(price_changes) * 15  # Each price change costs 15 points

    # DOM vs median: stored as deviation in value field
    dom_median_events = [e for e in idx_events if e.signal_type == "idx.dom_vs_median"]
    if dom_median_events:
        deviation = dom_median_events[0].value or 0
        details["dom_vs_median"] = round(deviation, 1)
        # Negative = faster than median = good
        if deviation <= -7:
            pass  # keep full score
        elif deviation <= 0:
            score -= 5
        elif deviation <= 14:
            score -= 15
        else:
            score -= 30

    # Status progression
    status_events = [e for e in idx_events if e.signal_type == "idx.status_change"]
    if status_events:
        latest_val = status_events[0].value
        if latest_val == 2.0:  # pending/under contract
            details["status"] = "pending"
            score += 10  # bonus for going under contract
        elif latest_val == 3.0:  # sold
            details["status"] = "sold"
            score += 5
        elif latest_val == 1.0:
            details["status"] = "active"
        else:
            details["status"] = "unknown"

    return _clamp(score), details


async def calculate(
    session: AsyncSession,
    listing_id: uuid.UUID,
    tenant_id: uuid.UUID,
    plan: str = "starter",
    custom_weights: dict | None = None,
) -> ListingHealthScore:
    """Calculate composite health score and persist it."""
    weights = _resolve_weights(plan, custom_weights)
    available = set(weights.keys())

    # Calculate available sub-scores
    sub_scores: dict[str, tuple[int, dict]] = {}

    if "media" in available:
        sub_scores["media"] = await calculate_media_score(session, listing_id)
    if "content" in available:
        sub_scores["content"] = await calculate_content_score(session, listing_id, tenant_id)
    if "velocity" in available:
        sub_scores["velocity"] = await calculate_velocity_score(session, listing_id, tenant_id)
    if "syndication" in available:
        sub_scores["syndication"] = await calculate_syndication_score(session, listing_id)
    if "market" in available:
        sub_scores["market"] = await calculate_market_score(session, listing_id)

    # Composite
    overall = sum(
        sub_scores[k][0] * weights[k]
        for k in weights
        if k in sub_scores
    )

    now = datetime.now(timezone.utc)

    # Build signals snapshot
    signals = {k: {"score": v[0], "details": v[1]} for k, v in sub_scores.items()}

    # Upsert listing_health_scores
    values = {
        "tenant_id": tenant_id,
        "listing_id": listing_id,
        "overall_score": _clamp(overall),
        "media_score": sub_scores.get("media", (0, {}))[0],
        "content_score": sub_scores.get("content", (0, {}))[0],
        "velocity_score": sub_scores.get("velocity", (0, {}))[0],
        "syndication_score": sub_scores.get("syndication", (0, {}))[0],
        "market_score": sub_scores.get("market", (0, {}))[0],
        "weights": weights,
        "signals_snapshot": signals,
        "calculated_at": now,
    }

    stmt = pg_insert(ListingHealthScore).values(id=uuid.uuid4(), **values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["listing_id"],
        set_={k: v for k, v in values.items() if k != "listing_id"},
    )
    await session.execute(stmt)

    # Append to history
    session.add(HealthScoreHistory(
        tenant_id=tenant_id,
        listing_id=listing_id,
        overall_score=_clamp(overall),
        media_score=sub_scores.get("media", (0, {}))[0],
        content_score=sub_scores.get("content", (0, {}))[0],
        velocity_score=sub_scores.get("velocity", (0, {}))[0],
        syndication_score=sub_scores.get("syndication", (0, {}))[0],
        market_score=sub_scores.get("market", (0, {}))[0],
        calculated_at=now,
    ))

    await session.flush()

    # Return the upserted row
    result = await session.execute(
        select(ListingHealthScore).where(ListingHealthScore.listing_id == listing_id)
    )
    return result.scalar_one()


async def get_score(session: AsyncSession, listing_id: uuid.UUID) -> ListingHealthScore | None:
    """Read the cached health score for a listing."""
    result = await session.execute(
        select(ListingHealthScore).where(ListingHealthScore.listing_id == listing_id)
    )
    return result.scalar_one_or_none()


async def get_trend(
    session: AsyncSession, listing_id: uuid.UUID, days: int = 90
) -> list[dict]:
    """Get health score history for trend display."""
    cutoff = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=days)

    result = await session.execute(
        select(HealthScoreHistory)
        .where(
            HealthScoreHistory.listing_id == listing_id,
            HealthScoreHistory.calculated_at >= cutoff,
        )
        .order_by(HealthScoreHistory.calculated_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "date": row.calculated_at.isoformat(),
            "overall": row.overall_score,
            "media": row.media_score,
            "content": row.content_score,
            "velocity": row.velocity_score,
            "syndication": row.syndication_score,
            "market": row.market_score,
        }
        for row in rows
    ]
