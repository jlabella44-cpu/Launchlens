import pytest
import uuid
from sqlalchemy import select
from launchlens.services.events import emit_event
from launchlens.models.event import Event
from launchlens.models.outbox import Outbox


@pytest.mark.asyncio
async def test_emit_event_writes_event_row(db_session):
    tenant_id = str(uuid.uuid4())
    listing_id = str(uuid.uuid4())
    await emit_event(
        session=db_session,
        event_type="vision.completed",
        payload={"label_count": 5},
        tenant_id=tenant_id,
        listing_id=listing_id,
    )
    await db_session.flush()
    result = await db_session.execute(
        select(Event).where(Event.event_type == "vision.completed")
    )
    event = result.scalar_one()
    assert event.tenant_id == uuid.UUID(tenant_id)
    assert event.listing_id == uuid.UUID(listing_id)
    assert event.payload["label_count"] == 5


@pytest.mark.asyncio
async def test_emit_event_writes_outbox_row(db_session):
    tenant_id = str(uuid.uuid4())
    await emit_event(
        session=db_session,
        event_type="coverage.failed",
        payload={"reason": "no photos"},
        tenant_id=tenant_id,
    )
    await db_session.flush()
    result = await db_session.execute(
        select(Outbox).where(Outbox.event_type == "coverage.failed")
    )
    outbox = result.scalar_one()
    assert outbox.delivered_at is None


@pytest.mark.asyncio
async def test_emit_event_without_listing_id(db_session):
    tenant_id = str(uuid.uuid4())
    await emit_event(
        session=db_session,
        event_type="tenant.created",
        payload={"plan": "starter"},
        tenant_id=tenant_id,
    )
    await db_session.flush()
    result = await db_session.execute(
        select(Event).where(Event.event_type == "tenant.created")
    )
    event = result.scalar_one()
    assert event.listing_id is None
