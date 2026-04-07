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
    mock_kling.poll_task = AsyncMock(return_value={"url": "https://cdn.kling.ai/clip.mp4", "duration": 5, "credits": 0.14})

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
    # Template pads to 12 clips even from 3 source photos
    assert result["clip_count"] == 12
    assert "video_asset_id" in result

    videos = (await db_session.execute(select(VideoAsset))).scalars().all()
    assert len(videos) == 1
    assert videos[0].video_type == "ai_generated"
    assert videos[0].status == "ready"
    assert videos[0].clip_count == 12
    assert videos[0].duration_seconds == 60
    first_video_id = videos[0].id

    # Run again — should update existing record, not create a duplicate
    with patch("listingjet.agents.video.httpx.AsyncClient", return_value=mock_http_client):
        result2 = await agent.execute(ctx)

    assert result2["status"] == "ready"
    assert result2["video_asset_id"] == str(first_video_id)
    videos2 = (await db_session.execute(select(VideoAsset))).scalars().all()
    assert len(videos2) == 1  # Still only one record


@pytest.mark.asyncio
async def test_video_agent_emits_event(db_session, listing_for_video):
    listing, _ = listing_for_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_kling = MagicMock()
    mock_kling.generate_clip = AsyncMock(return_value="task_001")
    mock_kling.poll_task = AsyncMock(return_value={"url": "https://cdn.kling.ai/clip.mp4", "duration": 5, "credits": 0.14})
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


def _make_entry(room: str, score: int, asset_id=None):
    """Build a fake (PackageSelection, Asset, VisionResult) tuple for selection tests."""
    ps = MagicMock()
    asset = MagicMock()
    asset.id = asset_id or uuid.uuid4()
    asset.file_path = f"s3://bucket/{room}.jpg"
    vr = MagicMock()
    vr.room_label = room
    vr.quality_score = score
    return (ps, asset, vr)


def test_select_photos_fills_12_positions():
    """Full package: exterior, drones, 10 interiors → 12 distinct slots."""
    agent = VideoAgent(
        kling_provider=MagicMock(), storage_service=MagicMock(),
        video_stitcher=MagicMock(), session_factory=MagicMock(),
    )
    selections = (
        [_make_entry("exterior", 95), _make_entry("exterior_rear", 85)]
        + [_make_entry("drone", 90), _make_entry("drone", 80)]
        + [_make_entry("kitchen", 88), _make_entry("living_room", 87),
           _make_entry("primary_bedroom", 86), _make_entry("primary_bathroom", 80),
           _make_entry("dining_room", 78), _make_entry("bedroom", 75),
           _make_entry("bathroom", 70), _make_entry("office", 65),
           _make_entry("backyard", 60), _make_entry("garage", 55)]
    )
    selected = agent._select_photos(selections)
    assert len(selected) == 12
    # pos 1 = best exterior
    assert selected[0][2].room_label == "exterior"
    # pos 12 = drone
    assert selected[-1][2].room_label == "drone"
    # Interior slots 3-11 should be score-descending
    interior_scores = [s[2].quality_score for s in selected[2:11]]
    assert interior_scores == sorted(interior_scores, reverse=True)


def test_select_photos_pads_when_thin():
    """Only 3 photos available → pads to 12 by repetition."""
    agent = VideoAgent(
        kling_provider=MagicMock(), storage_service=MagicMock(),
        video_stitcher=MagicMock(), session_factory=MagicMock(),
    )
    selections = [
        _make_entry("exterior", 90),
        _make_entry("kitchen", 85),
        _make_entry("living_room", 80),
    ]
    selected = agent._select_photos(selections)
    assert len(selected) == 12
    # Position 1 = exterior
    assert selected[0][2].room_label == "exterior"


def test_select_photos_no_drone_uses_exterior_both_ends():
    """No drone available → positions 1 and 12 both exteriors."""
    agent = VideoAgent(
        kling_provider=MagicMock(), storage_service=MagicMock(),
        video_stitcher=MagicMock(), session_factory=MagicMock(),
    )
    selections = (
        [_make_entry("exterior", 95), _make_entry("exterior_rear", 85)]
        + [_make_entry("kitchen", 88), _make_entry("living_room", 87),
           _make_entry("primary_bedroom", 86), _make_entry("dining_room", 78)]
    )
    selected = agent._select_photos(selections)
    assert len(selected) == 12
    # Position 1 = best exterior
    assert selected[0][2].room_label == "exterior"
    # Position 12 = next exterior (exterior_rear), since no drones exist
    assert selected[-1][2].room_label in ("exterior", "exterior_rear")


def test_select_photos_excludes_floorplans():
    """Floorplans, diagrams, and other non-photo content are excluded from video."""
    agent = VideoAgent(
        kling_provider=MagicMock(), storage_service=MagicMock(),
        video_stitcher=MagicMock(), session_factory=MagicMock(),
    )
    selections = (
        [_make_entry("exterior", 95), _make_entry("drone", 90)]
        + [_make_entry("floorplan", 92)]  # should be excluded despite high score
        + [_make_entry("diagram", 88)]     # should be excluded
        + [_make_entry("kitchen", 85), _make_entry("living_room", 80),
           _make_entry("bedroom", 75), _make_entry("bathroom", 70)]
    )
    selected = agent._select_photos(selections)
    # Floorplan and diagram should not appear in any position
    rooms_in_video = [s[2].room_label for s in selected]
    assert "floorplan" not in rooms_in_video
    assert "diagram" not in rooms_in_video
    assert len(selected) == 12


def test_select_photos_excludes_low_quality():
    """Photos below quality floor (30%) are excluded."""
    agent = VideoAgent(
        kling_provider=MagicMock(), storage_service=MagicMock(),
        video_stitcher=MagicMock(), session_factory=MagicMock(),
    )
    low_id = uuid.uuid4()
    selections = (
        [_make_entry("exterior", 95)]
        + [_make_entry("living_room", 20, asset_id=low_id)]  # below 30% floor
        + [_make_entry("kitchen", 85), _make_entry("bedroom", 75)]
    )
    selected = agent._select_photos(selections)
    asset_ids = [s[1].id for s in selected]
    assert low_id not in asset_ids


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
