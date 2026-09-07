# tests/test_agents/test_social_cuts.py
import uuid
from unittest.mock import MagicMock

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.social_cuts import PLATFORM_SPECS, SocialCutAgent
from listingjet.models.listing import Listing, ListingState
from listingjet.models.video_asset import VideoAsset
from tests.test_agents.conftest import make_session_factory


def test_platform_specs_exist():
    assert "instagram" in PLATFORM_SPECS
    assert "tiktok" in PLATFORM_SPECS
    assert "facebook" in PLATFORM_SPECS
    assert "youtube_short" in PLATFORM_SPECS
    assert PLATFORM_SPECS["instagram"]["width"] == 1080
    assert PLATFORM_SPECS["instagram"]["height"] == 1920


@pytest.fixture
async def listing_with_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "600 Social Cut Dr"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    video = VideoAsset(
        tenant_id=tenant_id, listing_id=listing.id,
        s3_key=f"videos/{listing.id}/tour.mp4",
        video_type="ai_generated", duration_seconds=40, status="ready",
    )
    db_session.add(video)
    await db_session.flush()
    return listing, video


@pytest.mark.asyncio
async def test_social_cut_agent_creates_cuts(db_session, listing_with_video):
    listing, video = listing_with_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_storage = MagicMock()
    mock_storage.download = MagicMock(return_value=b"fake-video-bytes")
    mock_storage.upload = MagicMock(side_effect=lambda key="", data=b"", content_type="": key)

    mock_cutter = MagicMock()
    mock_cutter.create_cut = MagicMock(return_value=b"fake-cut-bytes")

    agent = SocialCutAgent(
        storage_service=mock_storage,
        video_cutter=mock_cutter,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["cut_count"] == 4  # instagram, tiktok, facebook, youtube_short

    await db_session.refresh(video)
    assert video.social_cuts is not None
    assert len(video.social_cuts) == 4
    platforms = [c["platform"] for c in video.social_cuts]
    assert "instagram" in platforms
    assert "facebook" in platforms


@pytest.mark.asyncio
async def test_social_cut_agent_prefers_tour_video_over_other_ready_videos(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "601 Tour Preference Dr"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    older_tour = VideoAsset(
        tenant_id=tenant_id, listing_id=listing.id,
        s3_key=f"videos/{listing.id}/tour.mp4",
        video_type="tour", duration_seconds=30, status="ready",
    )
    newer_professional = VideoAsset(
        tenant_id=tenant_id, listing_id=listing.id,
        s3_key=f"videos/{listing.id}/professional.mp4",
        video_type="professional", duration_seconds=60, status="ready",
    )
    db_session.add(older_tour)
    await db_session.flush()
    db_session.add(newer_professional)
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_storage = MagicMock()
    mock_storage.download = MagicMock(return_value=b"fake-video-bytes")
    mock_storage.upload = MagicMock(side_effect=lambda key="", data=b"", content_type="": key)

    mock_cutter = MagicMock()
    mock_cutter.create_cut = MagicMock(return_value=b"fake-cut-bytes")

    agent = SocialCutAgent(
        storage_service=mock_storage,
        video_cutter=mock_cutter,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["video_asset_id"] == str(older_tour.id)
    mock_storage.download.assert_called_once_with(older_tour.s3_key)


@pytest.mark.asyncio
async def test_social_cut_agent_skips_no_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id, address={"street": "No Cut St"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    agent = SocialCutAgent(
        storage_service=MagicMock(), video_cutter=MagicMock(),
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result.get("skipped") is True
