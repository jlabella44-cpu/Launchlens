"""Real-time usage dashboard — SSE stream of platform-wide stats for admins."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import StreamingResponse

from listingjet.api.deps import get_db_admin, require_superadmin
from listingjet.models.credit_account import CreditAccount
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter()


async def _collect_stats(db: AsyncSession) -> dict:
    """Snapshot of platform-wide usage metrics."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_tenants = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.deactivated_at.is_(None))
    )).scalar() or 0

    listings_today = (await db.execute(
        select(func.count(Listing.id)).where(Listing.created_at >= today)
    )).scalar() or 0

    active_pipelines = (await db.execute(
        select(func.count(Listing.id)).where(
            Listing.state.in_([
                ListingState.UPLOADING,
                ListingState.ANALYZING,
                ListingState.AWAITING_REVIEW,
                ListingState.IN_REVIEW,
                ListingState.EXPORTING,
            ])
        )
    )).scalar() or 0

    completed_today = (await db.execute(
        select(func.count(Listing.id)).where(
            Listing.state == ListingState.DELIVERED,
            Listing.updated_at >= today,
        )
    )).scalar() or 0

    total_credits = (await db.execute(
        select(func.coalesce(func.sum(CreditAccount.balance), 0))
    )).scalar() or 0

    by_state_rows = (await db.execute(
        select(Listing.state, func.count(Listing.id)).group_by(Listing.state)
    )).all()
    by_state = {row[0].value: row[1] for row in by_state_rows}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_tenants": total_tenants,
        "listings_today": listings_today,
        "active_pipelines": active_pipelines,
        "completed_today": completed_today,
        "total_credits_outstanding": int(total_credits),
        "by_state": by_state,
    }


@router.get("/usage-stream")
async def usage_stream(
    request: Request,
    _admin=Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """SSE stream of platform-wide usage stats, refreshed every 10 seconds."""

    async def event_gen():
        while True:
            if await request.is_disconnected():
                break
            try:
                stats = await _collect_stats(db)
                yield f"event: usage\ndata: {json.dumps(stats)}\n\n"
            except Exception:
                logger.exception("Error collecting usage stats")
            await asyncio.sleep(10)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
