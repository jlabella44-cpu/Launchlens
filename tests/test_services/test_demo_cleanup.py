import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.services.demo_cleanup import cleanup_expired_demos

_DEMO_TENANT = uuid.UUID(int=0)


async def _make_demo(db_session, expired=True):
    """Create a demo listing, optionally expired."""
    offset = timedelta(hours=-2) if expired else timedelta(hours=24)
    listing = Listing(
        tenant_id=_DEMO_TENANT,
        address={"street": "Demo St"},
        metadata_={},
        state=ListingState.DEMO,
        is_demo=True,
        demo_expires_at=datetime.now(timezone.utc) + offset,
    )
    db_session.add(listing)
    await db_session.flush()

    asset = Asset(
        tenant_id=_DEMO_TENANT,
        listing_id=listing.id,
        file_path=f"s3://bucket/demo/{listing.id}/photo.jpg",
        file_hash="demohash",
        state="uploaded",
    )
    db_session.add(asset)
    await db_session.flush()
    return listing


@pytest.mark.asyncio
async def test_cleanup_deletes_expired_demos(db_session):
    expired = await _make_demo(db_session, expired=True)
    active = await _make_demo(db_session, expired=False)

    result = await cleanup_expired_demos(db_session)

    assert result["deleted_listings"] == 1
    assert result["deleted_assets"] == 1

    # Expired should be gone
    assert await db_session.get(Listing, expired.id) is None
    # Active should remain
    remaining = await db_session.get(Listing, active.id)
    assert remaining is not None
    assert remaining.is_demo is True


@pytest.mark.asyncio
async def test_cleanup_no_expired_returns_zeros(db_session):
    await _make_demo(db_session, expired=False)

    result = await cleanup_expired_demos(db_session)

    assert result["deleted_listings"] == 0
    assert result["deleted_assets"] == 0


@pytest.mark.asyncio
async def test_cleanup_deletes_associated_assets(db_session):
    expired = await _make_demo(db_session, expired=True)

    # Add a second asset
    asset2 = Asset(
        tenant_id=_DEMO_TENANT,
        listing_id=expired.id,
        file_path=f"s3://bucket/demo/{expired.id}/photo_2.jpg",
        file_hash="demohash2",
        state="uploaded",
    )
    db_session.add(asset2)
    await db_session.flush()

    result = await cleanup_expired_demos(db_session)

    assert result["deleted_assets"] == 2
    remaining = (await db_session.execute(
        select(Asset).where(Asset.listing_id == expired.id)
    )).scalars().all()
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_cleanup_with_storage_deletes_s3(db_session):
    from unittest.mock import MagicMock

    expired = await _make_demo(db_session, expired=True)
    storage = MagicMock()

    result = await cleanup_expired_demos(db_session, storage=storage)

    assert result["s3_cleaned"] == 1
    storage.delete.assert_called_once()
