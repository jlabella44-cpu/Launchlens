"""Server-Sent Events endpoint for real-time pipeline progress."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import StreamingResponse

from listingjet.api.deps import get_current_user
from listingjet.database import get_db
from listingjet.models.event import Event
from listingjet.models.listing import Listing
from listingjet.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Pipeline event types clients care about
_PIPELINE_EVENTS = {
    "ingestion.completed", "vision_tier1.completed", "vision_tier2.completed",
    "coverage.completed", "packaging.completed", "content.completed",
    "brand.completed", "social_content.completed", "mls_export.completed",
    "pipeline.completed", "video.completed", "chapters.completed",
    "social_cuts.completed",
}


@router.get("/listings/{listing_id}/events")
async def listing_events(
    listing_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream of pipeline events for a listing."""
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    async def event_stream():
        last_seen_id = None
        while True:
            if await request.is_disconnected():
                break

            query = (
                select(Event)
                .where(Event.listing_id == str(listing_id))
                .order_by(Event.created_at.asc())
            )
            if last_seen_id:
                query = query.where(Event.id > last_seen_id)

            result = await db.execute(query)
            events = result.scalars().all()

            for event in events:
                if event.event_type in _PIPELINE_EVENTS or event.event_type.endswith(".failed"):
                    data = json.dumps({
                        "event_type": event.event_type,
                        "payload": event.payload,
                        "timestamp": event.created_at.isoformat() if event.created_at else None,
                    })
                    yield f"event: {event.event_type}\ndata: {data}\n\n"
                last_seen_id = event.id

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
