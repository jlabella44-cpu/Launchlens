# tests/test_agents/test_watermark.py
import io
import uuid
from unittest.mock import MagicMock

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.watermark import WatermarkAgent
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from tests.test_agents.conftest import make_session_factory


def _make_jpeg_bytes() -> bytes:
    """Create a minimal valid JPEG image in memory."""
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGB", (100, 60), color=(200, 100, 50))
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
async def listing_with_package(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "10 Watermark Ave"},
        metadata_={},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(listing)
    await db_session.flush()

    asset = Asset(
        listing_id=listing.id,
        tenant_id=tenant_id,
        file_path=f"listings/{listing.id}/photo_0.jpg",
        file_hash="deadbeef",
        state="uploaded",
    )
    db_session.add(asset)
    await db_session.flush()

    pkg = PackageSelection(
        tenant_id=tenant_id,
        listing_id=listing.id,
        asset_id=asset.id,
        channel="mls",
        position=0,
        selected_by="ai",
        composite_score=0.85,
    )
    db_session.add(pkg)
    await db_session.flush()

    return listing, asset


@pytest.fixture
async def listing_with_brand(db_session, listing_with_package):
    listing, asset = listing_with_package
    brand_kit = BrandKit(
        tenant_id=listing.tenant_id,
        brokerage_name="Acme Realty",
        primary_color="#2563EB",
    )
    db_session.add(brand_kit)
    await db_session.flush()
    return listing, asset


@pytest.mark.asyncio
async def test_watermark_agent_applies_overlay(db_session, listing_with_brand):
    listing, asset = listing_with_brand

    jpeg_bytes = _make_jpeg_bytes()
    mock_storage = MagicMock()
    mock_storage.download.return_value = jpeg_bytes
    mock_storage.upload.return_value = f"listings/{listing.id}/watermarked/{asset.id}.jpg"

    agent = WatermarkAgent(
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    result = await agent.execute(ctx)

    assert result["watermarked_count"] == 1
    mock_storage.download.assert_called_once()
    mock_storage.upload.assert_called_once()
    _, uploaded_bytes, content_type = mock_storage.upload.call_args[0]
    assert content_type == "image/jpeg"
    assert len(uploaded_bytes) > 0


@pytest.mark.asyncio
async def test_watermark_agent_fallback_no_brand_kit(db_session, listing_with_package):
    listing, asset = listing_with_package

    jpeg_bytes = _make_jpeg_bytes()
    mock_storage = MagicMock()
    mock_storage.download.return_value = jpeg_bytes
    mock_storage.upload.return_value = "wm_key"

    agent = WatermarkAgent(
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    # Should still complete using default watermark text
    assert result["watermarked_count"] == 1


@pytest.mark.asyncio
async def test_watermark_agent_skips_failed_photos(db_session, listing_with_package):
    listing, asset = listing_with_package

    mock_storage = MagicMock()
    mock_storage.download.side_effect = Exception("S3 error")

    agent = WatermarkAgent(
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    # Failed photos should be skipped, not raise
    assert result["watermarked_count"] == 0


@pytest.mark.asyncio
async def test_watermark_agent_empty_package(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "Empty Package Rd"},
        metadata_={},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(listing)
    await db_session.flush()

    mock_storage = MagicMock()

    agent = WatermarkAgent(
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(tenant_id))
    result = await agent.execute(ctx)

    assert result["watermarked_count"] == 0
    mock_storage.download.assert_not_called()
