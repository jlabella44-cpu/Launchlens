import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete

from listingjet.models.outbox import Outbox
from listingjet.services.outbox_poller import OutboxPoller


async def _clear_undelivered_outbox(db_session):
    """Remove all undelivered outbox rows so tests aren't affected by other tests' data."""
    await db_session.execute(delete(Outbox).where(Outbox.delivered_at.is_(None)))
    await db_session.flush()


@pytest.mark.asyncio
async def test_poller_marks_rows_delivered(db_session):
    await _clear_undelivered_outbox(db_session)

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
    poller._get_webhook_url = AsyncMock(return_value=None)

    # Use a savepoint so the FOR UPDATE SKIP LOCKED fallback doesn't
    # leave the transaction in an aborted state.
    async with db_session.begin_nested():
        await poller._process_batch(db_session)

    await db_session.refresh(outbox)
    assert outbox.delivered_at is not None


@pytest.mark.asyncio
async def test_poller_skips_already_delivered_rows(db_session):
    await _clear_undelivered_outbox(db_session)

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
    poller._get_webhook_url = AsyncMock(return_value=None)

    async with db_session.begin_nested():
        count = await poller._process_batch(db_session)
    assert count == 0


@pytest.mark.asyncio
async def test_poller_processes_multiple_rows(db_session):
    await _clear_undelivered_outbox(db_session)

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
    poller._get_webhook_url = AsyncMock(return_value=None)

    async with db_session.begin_nested():
        count = await poller._process_batch(db_session)
    assert count == 3
