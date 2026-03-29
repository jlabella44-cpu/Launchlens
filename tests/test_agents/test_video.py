# tests/test_agents/test_video.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.video import VideoAgent
from listingjet.models.asset import Asset
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


def test_video_asset_model_exists():
    assert hasattr(VideoAsset, "listing_id")
    assert hasattr(VideoAsset, "video_type")
    assert hasattr(VideoAsset, "chapters")
    assert hasattr(VideoAsset, "social_cuts")
    assert hasattr(VideoAsset, "status")


@pytest.fixture
async def listing_for_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "100 Video Ln", "city": "Miami", "state": "FL"},
        metadata_={"beds": 3, "baths": 2, "sqft": 2000, "price": 500000},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(listing)
    await db_session.flush()

    rooms = ["exterior", "living_room", "kitchen"]
    assets = []
    for i, room in enumerate(rooms):
        a = Asset(
            tenant_id=tenant_id, listing_id=listing.id,
            file_path=f"listings/{listing.id}/{room}.jpg", file_hash=f"vid{i}", state="ingested",
        )
        db_session.add(a)
        assets.append(a)
    await db_session.flush()

    for i, (a, room) in enumerate(zip(assets, rooms)):
        vr = VisionResult(
            asset_id=a.id, tier=1,
            room_label=room, quality_score=90 - i * 5, commercial_score=80,
            hero_candidate=(i == 0),
        )
        db_session.add(vr)
        ps = PackageSelection(
            tenant_id=tenant_id, listing_id=listing.id, asset_id=a.id,
            channel="mls", position=i, composite_score=0.9 - i * 0.1, selected_by="ai",
        )
        db_session.add(ps)

    await db_session.flush()
    return listing, assets


@pytest.mark.asyncio
async def test_video_agent_creates_video_asset(db_session, listing_for_video):
    listing, assets = listing_for_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_kling = MagicMock()
    mock_kling.generate_clip = AsyncMock(return_value="task_001")
    mock_kling.poll_task = AsyncMock(return_value="https://cdn.kling.ai/clip.mp4")

    mock_storage = MagicMock()
    mock_storage.upload_bytes = MagicMock(return_value=f"videos/{listing.id}/tour.mp4")

    mock_stitcher = MagicMock()
    mock_stitcher.stitch = MagicMock(return_value=b"fake-mp4-bytes")

    mock_response = MagicMock()
    mock_response.content = b"fake-mp4-bytes"
    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)
    mock_http_client.get = AsyncMock(return_value=mock_response)

    agent = VideoAgent(
        kling_provider=mock_kling,
        storage_service=mock_storage,
        video_stitcher=mock_stitcher,
        session_factory=make_session_factory(db_session),
    )
    with patch("listingjet.agents.video.httpx.AsyncClient", return_value=mock_http_client):
        result = await agent.execute(ctx)

    assert result["status"] == "ready"
    assert result["clip_count"] == 3
    assert "video_asset_id" in result

    videos = (await db_session.execute(select(VideoAsset))).scalars().all()
    assert len(videos) == 1
    assert videos[0].video_type == "ai_generated"
    assert videos[0].status == "ready"
    assert videos[0].clip_count == 3


@pytest.mark.asyncio
async def test_video_agent_emits_event(db_session, listing_for_video):
    listing, _ = listing_for_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_kling = MagicMock()
    mock_kling.generate_clip = AsyncMock(return_value="task_001")
    mock_kling.poll_task = AsyncMock(return_value="https://cdn.kling.ai/clip.mp4")
    mock_storage = MagicMock()
    mock_storage.upload_bytes = MagicMock(return_value="videos/test.mp4")
    mock_stitcher = MagicMock()
    mock_stitcher.stitch = MagicMock(return_value=b"fake-mp4")

    mock_response = MagicMock()
    mock_response.content = b"fake-mp4"
    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)
    mock_http_client.get = AsyncMock(return_value=mock_response)

    agent = VideoAgent(
        kling_provider=mock_kling, storage_service=mock_storage,
        video_stitcher=mock_stitcher, session_factory=make_session_factory(db_session),
    )
    with patch("listingjet.agents.video.httpx.AsyncClient", return_value=mock_http_client):
        await agent.execute(ctx)

    from listingjet.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "video.completed")
    )).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_video_agent_handles_no_selections(db_session):
    """Listing with no package selections → skips video."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id, address={"street": "Empty St"}, metadata_={},
        state=ListingState.AWAITING_REVIEW,
    )
    db_session.add(listing)
    await db_session.flush()

    mock_kling = MagicMock()
    agent = VideoAgent(
        kling_provider=mock_kling, storage_service=MagicMock(),
        video_stitcher=MagicMock(), session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result.get("skipped") is True
