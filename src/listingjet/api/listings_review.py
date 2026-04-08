"""Listing review analytics — override rate, trust score trends."""
import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.database import get_db
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/review/analytics")
async def get_review_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get review override rate and trust score analytics for the tenant.

    Returns:
      - override_rate: % of photos changed by humans across all reviewed listings
      - override_rate_by_month: monthly trend showing if the AI is improving
      - avg_trust_score: average AI trust score across reviewed listings
      - total_reviewed: number of listings that went through human review
      - total_auto_approved: number of listings auto-approved
    """
    tenant_id = current_user.tenant_id

    reviewed_states = [ListingState.APPROVED, ListingState.DELIVERED, ListingState.EXPORTING]

    # Total selections and human overrides
    total_selections = (await db.execute(
        select(func.count(PackageSelection.id))
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            Listing.state.in_(reviewed_states),
        )
    )).scalar() or 0

    human_overrides = (await db.execute(
        select(func.count(PackageSelection.id))
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            PackageSelection.selected_by == "human",
            Listing.state.in_(reviewed_states),
        )
    )).scalar() or 0

    override_rate = (human_overrides / total_selections * 100) if total_selections > 0 else 0.0

    # Average trust score
    avg_trust = (await db.execute(
        select(func.avg(PackageSelection.composite_score))
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            Listing.state.in_(reviewed_states),
        )
    )).scalar() or 0.0

    # Total reviewed (went through human review) vs auto-approved
    from listingjet.models.event import Event
    total_reviewed = (await db.execute(
        select(func.count(func.distinct(Event.listing_id))).where(
            Event.tenant_id == tenant_id,
            Event.event_type == "listing.review_started",
        )
    )).scalar() or 0

    total_auto_approved = (await db.execute(
        select(func.count(func.distinct(Event.listing_id))).where(
            Event.tenant_id == tenant_id,
            Event.event_type == "packaging.completed",
            func.cast(Event.payload["auto_approved"], sa.Boolean).is_(True),
        )
    )).scalar() or 0

    # Monthly override rate trend (last 6 months)
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    monthly_result = await db.execute(
        select(
            extract("year", PackageSelection.created_at).label("year"),
            extract("month", PackageSelection.created_at).label("month"),
            func.count(PackageSelection.id).label("total"),
            func.sum(
                case((PackageSelection.selected_by == "human", 1), else_=0)
            ).label("overrides"),
        )
        .join(Listing, PackageSelection.listing_id == Listing.id)
        .where(
            PackageSelection.tenant_id == tenant_id,
            PackageSelection.created_at >= six_months_ago,
            Listing.state.in_(reviewed_states),
        )
        .group_by("year", "month")
        .order_by("year", "month")
    )

    override_trend = []
    for row in monthly_result:
        month_total = row.total or 0
        month_overrides = row.overrides or 0
        rate = (month_overrides / month_total * 100) if month_total > 0 else 0.0
        override_trend.append({
            "month": f"{int(row.year)}-{int(row.month):02d}",
            "override_rate": round(rate, 1),
            "total_selections": month_total,
            "human_overrides": month_overrides,
        })

    return {
        "override_rate": round(override_rate, 1),
        "avg_trust_score": round(float(avg_trust), 1),
        "total_selections": total_selections,
        "human_overrides": human_overrides,
        "total_reviewed": total_reviewed,
        "total_auto_approved": total_auto_approved,
        "override_trend": override_trend,
    }
