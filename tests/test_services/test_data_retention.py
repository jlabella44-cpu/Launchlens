"""Tests for the data retention / cleanup service."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from launchlens.models.outbox import Outbox
from launchlens.models.listing import Listing
from launchlens.services.data_retention import (
    EXPORT_RETENTION_DAYS,
    OUTBOX_RETENTION_DAYS,
    cleanup_delivered_outbox,
    cleanup_expired_exports,
    run_all_retention,
)


@pytest.mark.asyncio
async def test_cleanup_delivered_outbox_removes_old_rows(db_session):
    """Outbox rows delivered > 30 days ago should be deleted."""
    old_date = datetime.now(timezone.utc) - timedelta(days=OUTBOX_RETENTION_DAYS + 5)
    tenant_id = uuid.uuid4()

    old_row = Outbox(
        id=uuid.uuid4(),
        event_type="listing.completed",
        payload={"test": True},
        tenant_id=tenant_id,
        published=True,
        delivered_at=old_date,
    )
    recent_row = Outbox(
        id=uuid.uuid4(),
        event_type="listing.completed",
        payload={"test": True},
        tenant_id=tenant_id,
        published=True,
        delivered_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add_all([old_row, recent_row])
    await db_session.commit()

    count = await cleanup_delivered_outbox(db_session)
    await db_session.commit()

    assert count >= 1

    # Recent row should still exist
    result = await db_session.execute(select(Outbox).where(Outbox.id == recent_row.id))
    assert result.scalar_one_or_none() is not None

    # Old row should be gone
    result2 = await db_session.execute(select(Outbox).where(Outbox.id == old_row.id))
    assert result2.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_cleanup_expired_exports_clears_paths(db_session):
    """Listings older than 90 days should have bundle paths cleared and S3 objects deleted."""
    tenant_id = uuid.uuid4()
    old_date = datetime.now(timezone.utc) - timedelta(days=EXPORT_RETENTION_DAYS + 10)

    listing = Listing(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        address={"street": "1 Retention Rd"},
        metadata_={},
        state="delivered",
        mls_bundle_path="s3://bucket/mls/old.zip",
        marketing_bundle_path="s3://bucket/marketing/old.zip",
    )
    db_session.add(listing)
    await db_session.commit()

    # Manually set created_at to old date (after insert since server_default)
    listing.created_at = old_date
    await db_session.commit()

    mock_storage = MagicMock()
    result = await cleanup_expired_exports(db_session, storage=mock_storage)
    await db_session.commit()

    assert result["listings_cleaned"] >= 1
    assert result["s3_deleted"] >= 2
    assert mock_storage.delete.call_count >= 2

    # Paths should be cleared
    await db_session.refresh(listing)
    assert listing.mls_bundle_path is None
    assert listing.marketing_bundle_path is None


@pytest.mark.asyncio
async def test_run_all_retention_aggregates_results(db_session):
    """run_all_retention should call both sub-cleanups and merge results."""
    result = await run_all_retention(db_session, storage=None)
    assert "outbox_deleted" in result
    assert "listings_cleaned" in result
    assert "s3_deleted" in result
