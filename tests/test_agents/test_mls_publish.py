"""Tests for the MLS Publish agent."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.mls_publish import MLSPublishAgent
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.mls_connection import MLSConnection
from listingjet.models.mls_publish_record import MLSPublishRecord, PublishStatus
from listingjet.models.outbox import Outbox
from listingjet.models.package_selection import PackageSelection
from listingjet.models.vision_result import VisionResult

from .conftest import make_session_factory


async def _setup_delivered_listing_with_connection(db_session):
    """Create a DELIVERED listing with photos, vision results, and an active MLS connection."""
    tenant_id = uuid.uuid4()

    # MLS connection
    conn = MLSConnection(
        tenant_id=tenant_id,
        name="Test MLS",
        mls_board="TestBoard",
        reso_api_url="https://api.test-mls.com/reso",
        oauth_token_url="https://api.test-mls.com/oauth2/token",
        client_id="test-client",
        client_secret_encrypted="test-secret",
        is_active=True,
        config={},
    )
    db_session.add(conn)

    # Listing
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "200 Publish Way", "city": "Miami", "state": "FL", "zip": "33101"},
        metadata_={"beds": 4, "baths": 3, "sqft": 2400, "price": 750000, "property_type": "single_family"},
        state=ListingState.DELIVERED,
    )
    db_session.add(listing)
    await db_session.flush()

    # Assets + Package + Vision
    assets = []
    for i in range(3):
        a = Asset(
            listing_id=listing.id,
            tenant_id=tenant_id,
            file_path=f"listings/{listing.id}/photos/photo_{i}.jpg",
            file_hash=f"hash{i:03d}",
            state="uploaded",
        )
        db_session.add(a)
        assets.append(a)
    await db_session.flush()

    room_labels = ["exterior_front", "kitchen", "living_room"]
    for i, a in enumerate(assets):
        pkg = PackageSelection(
            tenant_id=tenant_id,
            listing_id=listing.id,
            asset_id=a.id,
            channel="mls",
            position=i,
            selected_by="ai",
            composite_score=0.9 - i * 0.1,
        )
        db_session.add(pkg)

        vr = VisionResult(
            asset_id=a.id,
            tier=1,
            room_label=room_labels[i],
            is_interior=(i > 0),
            quality_score=90 - i * 5,
            commercial_score=85,
            hero_candidate=(i == 0),
            hero_explanation=f"Caption for {room_labels[i]}",
            raw_labels={},
            model_used="test-model",
        )
        db_session.add(vr)
    await db_session.flush()

    return listing, tenant_id, conn


def _make_mock_adapter():
    """Create a mock RESO adapter that simulates successful submission."""
    adapter = MagicMock()
    adapter.submit_property = AsyncMock(
        return_value={
            "ListingKey": "MLS-TEST-001",
            "ListingId": "P-TEST-001",
        }
    )
    adapter.submit_media = AsyncMock(
        return_value={
            "listing_key": "MLS-TEST-001",
            "accepted": 3,
            "rejected": 0,
            "errors": [],
        }
    )
    return adapter


def _make_storage_service():
    """Create a mock storage service."""
    storage = MagicMock()
    storage.presigned_url = MagicMock(return_value="https://s3.example.com/presigned/photo.jpg")
    return storage


@pytest.mark.asyncio
async def test_mls_publish_submits_property_and_media(db_session):
    listing, tenant_id, conn = await _setup_delivered_listing_with_connection(db_session)

    adapter = _make_mock_adapter()
    storage = _make_storage_service()

    agent = MLSPublishAgent(
        storage_service=storage,
        session_factory=make_session_factory(db_session),
        reso_adapter=adapter,
        content_result={"mls_safe": "Beautiful 4BR home in Miami."},
    )

    result = await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id)))

    assert result["status"] == "submitted"
    assert result["reso_listing_key"] == "MLS-TEST-001"
    assert result["photos_submitted"] == 3
    assert result["photos_accepted"] == 3

    # Verify adapter was called correctly
    adapter.submit_property.assert_called_once()
    prop_payload = adapter.submit_property.call_args[0][0]
    assert prop_payload["City"] == "Miami"
    assert prop_payload["ListPrice"] == 750000
    assert prop_payload["BedroomsTotal"] == 4
    assert "Beautiful 4BR home" in prop_payload["PublicRemarks"]

    adapter.submit_media.assert_called_once()
    media_args = adapter.submit_media.call_args
    assert media_args[0][0] == "MLS-TEST-001"
    assert len(media_args[0][1]) == 3


@pytest.mark.asyncio
async def test_mls_publish_creates_record(db_session):
    listing, tenant_id, conn = await _setup_delivered_listing_with_connection(db_session)

    agent = MLSPublishAgent(
        storage_service=_make_storage_service(),
        session_factory=make_session_factory(db_session),
        reso_adapter=_make_mock_adapter(),
    )

    await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id)))

    from sqlalchemy import select

    result = await db_session.execute(select(MLSPublishRecord).where(MLSPublishRecord.listing_id == listing.id))
    record = result.scalar_one()

    assert record.status == PublishStatus.SUBMITTED
    assert record.reso_listing_key == "MLS-TEST-001"
    assert record.photos_submitted == 3
    assert record.photos_accepted == 3
    assert record.connection_id == conn.id


@pytest.mark.asyncio
async def test_mls_publish_emits_event(db_session):
    listing, tenant_id, conn = await _setup_delivered_listing_with_connection(db_session)

    agent = MLSPublishAgent(
        storage_service=_make_storage_service(),
        session_factory=make_session_factory(db_session),
        reso_adapter=_make_mock_adapter(),
    )

    await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id)))

    from sqlalchemy import select

    result = await db_session.execute(select(Outbox).where(Outbox.event_type == "mls_publish.completed"))
    outbox_row = result.scalar_one_or_none()
    assert outbox_row is not None
    assert outbox_row.listing_id == listing.id


@pytest.mark.asyncio
async def test_mls_publish_fails_without_connection(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "999 No MLS Rd", "city": "Nowhere", "state": "TX"},
        metadata_={},
        state=ListingState.DELIVERED,
    )
    db_session.add(listing)
    await db_session.flush()

    agent = MLSPublishAgent(
        storage_service=_make_storage_service(),
        session_factory=make_session_factory(db_session),
    )

    with pytest.raises(RuntimeError, match="No active MLS connection"):
        await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id)))


@pytest.mark.asyncio
async def test_mls_publish_property_submission_failure(db_session):
    listing, tenant_id, conn = await _setup_delivered_listing_with_connection(db_session)

    adapter = MagicMock()
    adapter.submit_property = AsyncMock(side_effect=RuntimeError("RESO API down"))

    agent = MLSPublishAgent(
        storage_service=_make_storage_service(),
        session_factory=make_session_factory(db_session),
        reso_adapter=adapter,
    )

    with pytest.raises(RuntimeError, match="RESO API down"):
        await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id)))

    # Verify listing reverted to DELIVERED
    await db_session.refresh(listing)
    assert listing.state == ListingState.DELIVERED

    # Verify publish record marked as failed
    from sqlalchemy import select

    result = await db_session.execute(select(MLSPublishRecord).where(MLSPublishRecord.listing_id == listing.id))
    record = result.scalar_one()
    assert record.status == PublishStatus.FAILED
    assert "RESO API down" in record.error_message


@pytest.mark.asyncio
async def test_mls_publish_sets_publishing_state(db_session):
    """Verify listing transitions through PUBLISHING during submission."""
    listing, tenant_id, conn = await _setup_delivered_listing_with_connection(db_session)

    states_seen = []

    original_submit = AsyncMock(
        return_value={
            "ListingKey": "MLS-TEST-002",
            "ListingId": "P-TEST-002",
        }
    )

    async def _track_state(*args, **kwargs):
        await db_session.refresh(listing)
        states_seen.append(listing.state)
        return await original_submit(*args, **kwargs)

    adapter = MagicMock()
    adapter.submit_property = AsyncMock(side_effect=_track_state)
    adapter.submit_media = AsyncMock(
        return_value={
            "listing_key": "MLS-TEST-002",
            "accepted": 3,
            "rejected": 0,
            "errors": [],
        }
    )

    agent = MLSPublishAgent(
        storage_service=_make_storage_service(),
        session_factory=make_session_factory(db_session),
        reso_adapter=adapter,
    )

    await agent.execute(AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id)))

    assert ListingState.PUBLISHING in states_seen
