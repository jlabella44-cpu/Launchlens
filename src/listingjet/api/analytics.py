"""
Analytics API — pipeline performance metrics per tenant.

Endpoints:
  GET /analytics/overview  — listings by state, total processed, avg pipeline time
  GET /analytics/timeline  — daily listing counts for the past N days
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, get_db
from listingjet.models.event import Event
from listingjet.models.listing import Listing, ListingState
from listingjet.models.user import User

router = APIRouter()


@router.get("/overview")
async def analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pipeline performance overview for the current tenant."""
    tid = current_user.tenant_id

    # Listings by state
    state_rows = (await db.execute(
        select(Listing.state, func.count(Listing.id))
        .where(Listing.tenant_id == tid)
        .group_by(Listing.state)
    )).all()
    by_state = {
        row[0].value if hasattr(row[0], "value") else row[0]: row[1]
        for row in state_rows
    }

    total = sum(by_state.values())
    delivered = by_state.get("delivered", 0)

    # Avg time from creation to delivery (for delivered listings)
    avg_result = await db.execute(
        select(
            func.avg(
                extract("epoch", Listing.updated_at) - extract("epoch", Listing.created_at)
            )
        ).where(
            Listing.tenant_id == tid,
            Listing.state == ListingState.DELIVERED,
        )
    )
    avg_seconds = avg_result.scalar()
    avg_pipeline_minutes = round(avg_seconds / 60, 1) if avg_seconds else None

    # Success rate (delivered / total non-demo)
    non_demo = total - by_state.get("demo", 0)
    success_rate = round(delivered / non_demo * 100, 1) if non_demo > 0 else None

    # Event counts by type (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    event_rows = (await db.execute(
        select(Event.event_type, func.count(Event.id))
        .where(
            Event.tenant_id == tid,
            Event.created_at >= thirty_days_ago,
        )
        .group_by(Event.event_type)
    )).all()
    events_by_type = {row[0]: row[1] for row in event_rows}

    return {
        "total_listings": total,
        "delivered": delivered,
        "by_state": by_state,
        "avg_pipeline_minutes": avg_pipeline_minutes,
        "success_rate_pct": success_rate,
        "events_last_30d": events_by_type,
    }


@router.get("/timeline")
async def analytics_timeline(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily listing creation counts for the past N days."""
    tid = current_user.tenant_id
    start = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (await db.execute(
        select(
            func.date(Listing.created_at).label("day"),
            func.count(Listing.id).label("count"),
        )
        .where(
            Listing.tenant_id == tid,
            Listing.created_at >= start,
        )
        .group_by(func.date(Listing.created_at))
        .order_by(func.date(Listing.created_at))
    )).all()

    return {
        "days": days,
        "data": [{"date": str(row[0]), "count": row[1]} for row in rows],
    }
