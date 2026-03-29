# src/listingjet/services/events.py
"""
Event emission service — Outbox Pattern.

USAGE: Always call emit_event() within an existing SQLAlchemy session that
is part of a broader state-change transaction. Do NOT commit inside this
function — the caller commits, which atomically persists both the state
change AND the event.

  async with session.begin():
      listing.status = "vision_complete"
      await emit_event(session, "vision.completed", {...}, tenant_id=...)
      # single commit covers both
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.event import Event
from listingjet.models.outbox import Outbox


async def emit_event(
    session: AsyncSession,
    event_type: str,
    payload: dict,
    tenant_id: str,
    listing_id: str | None = None,
) -> Event:
    """
    Write an Event row and an Outbox row in the caller's transaction.
    Returns the Event ORM object (not yet flushed — caller controls that).
    """
    tid = uuid.UUID(tenant_id)
    lid = uuid.UUID(listing_id) if listing_id else None

    event = Event(
        event_type=event_type,
        payload=payload,
        tenant_id=tid,
        listing_id=lid,
        created_at=datetime.now(timezone.utc),
    )
    outbox = Outbox(
        event_type=event_type,
        payload=payload,
        tenant_id=tid,
        listing_id=lid,
        created_at=datetime.now(timezone.utc),
        delivered_at=None,
    )

    session.add(event)
    session.add(outbox)
    return event
