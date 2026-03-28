# tests/test_agents/test_chapter.py
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from launchlens.agents.base import AgentContext
from launchlens.agents.chapter import ChapterAgent
from launchlens.models.listing import Listing, ListingState
from launchlens.models.video_asset import VideoAsset
from tests.test_agents.conftest import make_session_factory

MOCK_CHAPTER_RESPONSE = json.dumps({
    "chapters": [
        {"time": 0, "label": "exterior", "description": "Front entrance and curb appeal"},
        {"time": 12, "label": "living_room", "description": "Open-concept living area"},
        {"time": 25, "label": "kitchen", "description": "Modern kitchen with island"},
        {"time": 38, "label": "primary_bedroom", "description": "Spacious primary suite"},
        {"time": 50, "label": "backyard", "description": "Private backyard with patio"},
    ]
})


@pytest.fixture
async def listing_with_pro_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "500 Pro Video Dr"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    video = VideoAsset(
        tenant_id=tenant_id, listing_id=listing.id,
        s3_key=f"videos/{listing.id}/pro-tour.mp4",
        video_type="professional", duration_seconds=60,
        status="ready",
    )
    db_session.add(video)
    await db_session.flush()
    return listing, video


@pytest.mark.asyncio
async def test_chapter_agent_adds_chapters(db_session, listing_with_pro_video):
    listing, video = listing_with_pro_video
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_CHAPTER_RESPONSE)

    agent = ChapterAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["chapter_count"] == 5

    await db_session.refresh(video)
    assert video.chapters is not None
    assert len(video.chapters) == 5
    assert video.chapters[0]["label"] == "exterior"


@pytest.mark.asyncio
async def test_chapter_agent_skips_when_no_video(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id, address={"street": "No Video St"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    agent = ChapterAgent(
        vision_provider=MagicMock(),
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)
    assert result.get("skipped") is True
