import uuid
from datetime import datetime, timezone

import pytest

from listingjet.models.outbox import Outbox
from listingjet.services.outbox_poller import OutboxPoller


@pytest.mark.asyncio
async def test_poller_marks_rows_delivered(db_session):
    tenant_id = uuid.uuid4()
    outbox = Outbox(
        event_type="test.event",
        payload={"x": 1},
        tenant_id=tenant_id,
        listing_id=None,
        created_at=datetime.now(timezone.utc),
        delivered_at=None,
    )
    db_session.add(outbox)
    await db_session.flush()

    poller = OutboxPoller(session_factory=None)
    await poller._process_batch(db_session)

    await db_session.refresh(outbox)
    assert outbox.delivered_at is not None


@pytest.mark.asyncio
async def test_poller_skips_already_delivered_rows(db_session):
    tenant_id = uuid.uuid4()
    already_delivered = datetime.now(timezone.utc)
    outbox = Outbox(
        event_type="test.event",
        payload={"x": 2},
        tenant_id=tenant_id,
        listing_id=None,
        created_at=already_delivered,
        delivered_at=already_delivered,
    )
    db_session.add(outbox)
    await db_session.flush()

    poller = OutboxPoller(session_factory=None)
    count = await poller._process_batch(db_session)
    assert count == 0


@pytest.mark.asyncio
async def test_poller_processes_multiple_rows(db_session):
    tenant_id = uuid.uuid4()
    for i in range(3):
        db_session.add(Outbox(
            event_type=f"test.event.{i}",
            payload={"i": i},
            tenant_id=tenant_id,
            listing_id=None,
            created_at=datetime.now(timezone.utc),
            delivered_at=None,
        ))
    await db_session.flush()

    poller = OutboxPoller(session_factory=None)
    count = await poller._process_batch(db_session)
    assert count == 3
