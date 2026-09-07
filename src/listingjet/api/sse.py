"""Server-Sent Events endpoint for real-time pipeline progress."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import StreamingResponse

from listingjet.api.deps import get_current_user_or_query_token
from listingjet.database import AsyncSessionLocal, get_db
from listingjet.models.event import Event
from listingjet.models.listing import Listing
from listingjet.models.user import User
from listingjet.services.endpoint_rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Client reconnect backoff advertised as the first frame of every stream.
RETRY_MS = 5000

# Sentinel id used when seeding the cursor from a timestamp only (an unknown
# `Last-Event-ID`): sorts before every real UUID at that instant.
_MIN_UUID = uuid.UUID(int=0)

# Pipeline event types clients care about
_PIPELINE_EVENTS = {
    "ingestion.completed", "photo_analysis.completed", "photo_compliance.completed",
    "coverage.completed", "packaging.completed", "content_social.completed",
    "brand.completed", "mls_export.completed",
    "pipeline.completed", "video_baseline.completed", "video_ai.completed",
    "social_cuts.completed",
}


def _session_factory():
    """Short-lived session for one poll iteration.

    Indirection so tests can point the stream at the test engine — the
    injected request session must not be held open across the stream.
    """
    return AsyncSessionLocal()


async def _seed_cursor(db: AsyncSession, listing_id: uuid.UUID, last_event_id: str | None):
    """Resolve a `Last-Event-ID` header into a `(created_at, id)` cursor.

    Returns `(None, None)` when there is no header (a fresh connect replays
    the listing's history). An unknown or malformed id means the client has
    state we can't place, so we start from *now* rather than replaying
    everything.
    """
    if not last_event_id:
        return None, None
    try:
        event_uuid = uuid.UUID(last_event_id)
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc), _MIN_UUID
    event = (await db.execute(
        select(Event).where(Event.id == event_uuid, Event.listing_id == str(listing_id))
    )).scalar_one_or_none()
    if event is None or event.created_at is None:
        return datetime.now(timezone.utc), _MIN_UUID
    return event.created_at, event.id


@router.get("/listings/{listing_id}/events")
async def listing_events(
    listing_id: uuid.UUID,
    request: Request,
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(get_current_user_or_query_token),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream of pipeline events for a listing."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    tenant_id = str(current_user.tenant_id)
    start_created, start_id = await _seed_cursor(db, listing_id, request.headers.get("last-event-id"))

    async def event_stream():
        yield f"retry: {RETRY_MS}\n\n"

        last_created, last_id = start_created, start_id
        while True:
            if await request.is_disconnected():
                break

            # A fresh, short-lived session per poll: the injected request
            # session must not be pinned to a connection for the lifetime
            # of a long-running stream.
            async with _session_factory() as session:
                await session.execute(
                    text("SELECT set_config('app.current_tenant', :tid, true)"),
                    {"tid": tenant_id},
                )
                query = (
                    select(Event)
                    .where(Event.listing_id == str(listing_id))
                    .order_by(Event.created_at, Event.id)
                )
                if last_created is not None:
                    query = query.where(
                        tuple_(Event.created_at, Event.id) > (last_created, last_id)
                    )
                events = (await session.execute(query)).scalars().all()

            for event in events:
                if event.event_type in _PIPELINE_EVENTS or event.event_type.endswith(".failed"):
                    data = json.dumps({
                        "event_type": event.event_type,
                        "payload": event.payload,
                        "timestamp": event.created_at.isoformat() if event.created_at else None,
                    })
                    yield f"id: {event.id}\nevent: {event.event_type}\ndata: {data}\n\n"
                last_created, last_id = event.created_at, event.id

            await asyncio.sleep(2)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
