# tests/test_agents/test_floorplan.py
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.floorplan import FLOORPLAN_EXTRACTION_PROMPT, FloorplanAgent
from listingjet.models.asset import Asset
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing, ListingState
from listingjet.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


def test_dollhouse_scene_model_exists():
    from listingjet.models.dollhouse_scene import DollhouseScene
    assert hasattr(DollhouseScene, "listing_id")
    assert hasattr(DollhouseScene, "scene_json")
    assert hasattr(DollhouseScene, "room_count")


MOCK_GPT4V_RESPONSE = json.dumps({
    "rooms": [
        {
            "label": "living_room",
            "polygon": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.4], [0.0, 0.4]],
            "width_meters": 6.0, "height_meters": 4.5,
            "doors": [{"wall": "south", "position": 0.5}],
            "windows": [{"wall": "east", "position": 0.3}],
        },
        {
            "label": "kitchen",
            "polygon": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.4], [0.5, 0.4]],
            "width_meters": 5.0, "height_meters": 4.5,
            "doors": [{"wall": "west", "position": 0.5}],
            "windows": [],
        },
        {
            "label": "bedroom",
            "polygon": [[0.0, 0.4], [0.5, 0.4], [0.5, 1.0], [0.0, 1.0]],
            "width_meters": 6.0, "height_meters": 5.0,
            "doors": [{"wall": "north", "position": 0.3}],
            "windows": [{"wall": "west", "position": 0.5}],
        },
    ],
    "overall_width_meters": 12.0,
    "overall_height_meters": 9.0,
})


@pytest.fixture
async def listing_with_floorplan(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "300 Dollhouse Dr", "city": "Austin", "state": "TX"},
        metadata_={"beds": 2, "baths": 1, "sqft": 1200, "price": 300000},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    photo_rooms = ["living_room", "kitchen", "bedroom"]
    photos = []
    for i, room in enumerate(photo_rooms):
        a = Asset(
            tenant_id=tenant_id, listing_id=listing.id,
            file_path=f"listings/{listing.id}/{room}.jpg", file_hash=f"photo{i}", state="ingested",
        )
        db_session.add(a)
        photos.append(a)
    await db_session.flush()

    for i, (a, room) in enumerate(zip(photos, photo_rooms)):
        vr = VisionResult(
            asset_id=a.id,
            tier=1, room_label=room,
            quality_score=90 - i * 5, commercial_score=80, hero_candidate=(i == 0),
        )
        db_session.add(vr)

    floorplan = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/floorplan.jpg", file_hash="fp001", state="ingested",
    )
    db_session.add(floorplan)
    await db_session.flush()
    return listing, floorplan, photos


@pytest.mark.asyncio
async def test_floorplan_agent_creates_scene(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_GPT4V_RESPONSE)

    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    result = await agent.execute(ctx)

    assert result["room_count"] == 3
    assert "scene_id" in result

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    assert len(scenes) == 1
    assert scenes[0].listing_id == listing.id
    assert scenes[0].room_count == 3
    assert len(scenes[0].scene_json["rooms"]) == 3


@pytest.mark.asyncio
async def test_floorplan_agent_matches_photos_to_rooms(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_GPT4V_RESPONSE)

    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(ctx)

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    rooms_with_photos = [r for r in scenes[0].scene_json["rooms"] if r.get("best_photo_asset_id")]
    assert len(rooms_with_photos) == 3


@pytest.mark.asyncio
async def test_floorplan_agent_emits_event(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt = AsyncMock(return_value=MOCK_GPT4V_RESPONSE)

    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    await agent.execute(ctx)

    from listingjet.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "floorplan.completed")
    )).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_floorplan_agent_no_floorplan_skips(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "No Floor St"}, metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    mock_vision = MagicMock()
    agent = FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["room_count"] == 0
    assert result.get("skipped") is True


def test_extraction_prompt_exists():
    assert "rooms" in FLOORPLAN_EXTRACTION_PROMPT
    assert "polygon" in FLOORPLAN_EXTRACTION_PROMPT
    assert "JSON" in FLOORPLAN_EXTRACTION_PROMPT
