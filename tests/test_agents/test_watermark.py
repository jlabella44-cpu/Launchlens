import io
import uuid
from unittest.mock import MagicMock

import pytest
from PIL import Image

from launchlens.agents.base import AgentContext
from launchlens.agents.watermark import WatermarkAgent
from launchlens.models.asset import Asset
from launchlens.models.listing import Listing, ListingState
from launchlens.models.package_selection import PackageSelection
from tests.test_agents.conftest import make_session_factory


def _make_jpeg():
    img = Image.new("RGB", (100, 100), "red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_apply_watermark_returns_bytes():
    agent = WatermarkAgent.__new__(WatermarkAgent)
    jpeg_bytes = _make_jpeg()
    result = agent._apply_watermark(jpeg_bytes)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Verify it's a valid JPEG
    img = Image.open(io.BytesIO(result))
    assert img.format == "JPEG"


def test_apply_watermark_handles_invalid_input():
    agent = WatermarkAgent.__new__(WatermarkAgent)
    bad_bytes = b"not-an-image"
    result = agent._apply_watermark(bad_bytes)
    assert result == bad_bytes


@pytest.mark.asyncio
async def test_watermark_agent_execute(db_session, listing, assets):
    listing.state = ListingState.APPROVED
    await db_session.flush()

    # Create PackageSelection rows for each asset
    for i, asset in enumerate(assets):
        ps = PackageSelection(
            tenant_id=listing.tenant_id,
            listing_id=listing.id,
            asset_id=asset.id,
            channel="mls",
            position=i,
            selected_by="ai",
            composite_score=0.9 - i * 0.1,
        )
        db_session.add(ps)
    await db_session.flush()

    jpeg_bytes = _make_jpeg()

    # Mock StorageService
    mock_storage = MagicMock()
    mock_storage.download.return_value = jpeg_bytes
    upload_calls = []

    def track_upload(key, data, content_type):
        upload_calls.append({"key": key, "data": data, "content_type": content_type})
        return key

    mock_storage.upload.side_effect = track_upload

    agent = WatermarkAgent(
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["watermarked_count"] == 3
    assert result["listing_id"] == str(listing.id)

    # Verify storage interactions
    assert mock_storage.download.call_count == 3
    assert mock_storage.upload.call_count == 3

    # Verify upload keys follow expected pattern
    for call in upload_calls:
        assert call["key"].startswith(f"listings/{listing.id}/watermarked/")
        assert call["content_type"] == "image/jpeg"
        # Verify uploaded data is valid JPEG
        img = Image.open(io.BytesIO(call["data"]))
        assert img.format == "JPEG"
