# tests/test_agents/test_floorplan.py
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.floorplan import FLOORPLAN_DOLLHOUSE_PROMPT, FloorplanAgent
from listingjet.models.asset import Asset
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing, ListingState
from listingjet.models.vision_result import VisionResult
from tests.test_agents.conftest import make_session_factory


def _fake_storage():
    """Stub storage that turns an S3 key into a fake HTTP URL."""
    storage = MagicMock()
    storage.presigned_url = MagicMock(
        side_effect=lambda key, expires_in=3600: f"https://fake.example/{key}"
    )
    return storage


def test_dollhouse_scene_model_exists():
    from listingjet.models.dollhouse_scene import DollhouseScene
    assert hasattr(DollhouseScene, "listing_id")
    assert hasattr(DollhouseScene, "scene_json")
    assert hasattr(DollhouseScene, "room_count")


def _floor_response(floor_label="First Floor", level=1):
    return json.dumps({
        "floor_label": floor_label,
        "level": level,
        "structure": "main_house",
        "overall_width_meters": 12.0,
        "overall_height_meters": 9.0,
        "wall_height_meters": 2.7,
        "rooms": [
            {
                "label": "living_room",
                "polygon": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.4], [0.0, 0.4]],
                "width_meters": 6.0, "height_meters": 4.5,
                "doors": [{"wall": "south", "position": 0.5}],
                "windows": [{"wall": "east", "position": 0.3}],
                "wall_color": "#E8E2D0",
                "flooring": "hardwood",
                "decor_tags": ["beige walls"],
                "furniture": [
                    {"type": "sectional", "x": 0.3, "y": 0.5, "rotation_degrees": 0},
                ],
            },
            {
                "label": "kitchen",
                "polygon": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.4], [0.5, 0.4]],
                "width_meters": 5.0, "height_meters": 4.5,
                "doors": [{"wall": "west", "position": 0.5}],
                "windows": [],
                "wall_color": "#FFFFFF",
                "flooring": "tile",
                "decor_tags": [],
                "furniture": [
                    {"type": "kitchen_island", "x": 0.5, "y": 0.5, "rotation_degrees": 0},
                ],
            },
            {
                "label": "bedroom",
                "polygon": [[0.0, 0.4], [0.5, 0.4], [0.5, 1.0], [0.0, 1.0]],
                "width_meters": 6.0, "height_meters": 5.0,
                "doors": [{"wall": "north", "position": 0.3}],
                "windows": [{"wall": "west", "position": 0.5}],
                "wall_color": "#D6CFC4",
                "flooring": "carpet",
                "decor_tags": [],
                "furniture": [
                    {"type": "queen_bed", "x": 0.5, "y": 0.5, "rotation_degrees": 0},
                ],
            },
        ],
    })


MOCK_FLOOR_RESPONSE = _floor_response()


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

    # Tag the floorplan asset so vision-based detection finds it.
    db_session.add(VisionResult(
        asset_id=floorplan.id,
        tier=1, room_label="floorplan",
        quality_score=50, commercial_score=0, hero_candidate=False,
    ))
    await db_session.flush()
    return listing, floorplan, photos


def _make_agent(db_session, mock_vision):
    return FloorplanAgent(
        vision_provider=mock_vision,
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
    )


@pytest.mark.asyncio
async def test_floorplan_agent_creates_scene(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt_multi = AsyncMock(return_value=MOCK_FLOOR_RESPONSE)

    agent = _make_agent(db_session, mock_vision)
    result = await agent.execute(ctx)

    assert result["room_count"] == 3
    assert result["floor_count"] == 1
    assert "scene_id" in result

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    assert len(scenes) == 1
    assert scenes[0].listing_id == listing.id
    assert scenes[0].room_count == 3

    scene_json = scenes[0].scene_json
    assert scene_json["version"] == 2
    assert len(scene_json["floors"]) == 1
    floor = scene_json["floors"][0]
    assert floor["floor_label"] == "First Floor"
    assert floor["level"] == 1
    assert floor["structure"] == "main_house"
    assert len(floor["rooms"]) == 3

    living = next(r for r in floor["rooms"] if r["label"] == "living_room")
    assert living["wall_color"] == "#E8E2D0"
    assert living["flooring"] == "hardwood"
    assert living["furniture"][0]["type"] == "sectional"


@pytest.mark.asyncio
async def test_floorplan_agent_matches_photos_to_rooms(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt_multi = AsyncMock(return_value=MOCK_FLOOR_RESPONSE)

    agent = _make_agent(db_session, mock_vision)
    await agent.execute(ctx)

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    rooms = scenes[0].scene_json["floors"][0]["rooms"]
    rooms_with_photos = [r for r in rooms if r.get("best_photo_asset_id")]
    assert len(rooms_with_photos) == 3


@pytest.mark.asyncio
async def test_floorplan_agent_emits_event(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt_multi = AsyncMock(return_value=MOCK_FLOOR_RESPONSE)

    agent = _make_agent(db_session, mock_vision)
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
    agent = _make_agent(db_session, mock_vision)
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["room_count"] == 0
    assert result.get("skipped") is True


@pytest.mark.asyncio
async def test_floorplan_agent_detects_via_vision(db_session):
    """Asset with a UUID-like filename (no 'floorplan' in path) is still detected
    when VisionResult tags it with room_label='floorplan'."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "500 Vision Ln"},
        metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    uuid_name = uuid.uuid4().hex
    floorplan = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/{uuid_name}.jpg",
        file_hash="visfp01", state="ingested",
    )
    db_session.add(floorplan)
    await db_session.flush()

    db_session.add(VisionResult(
        asset_id=floorplan.id, tier=1, room_label="floorplan",
        quality_score=50, commercial_score=0, hero_candidate=False,
    ))
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt_multi = AsyncMock(return_value=MOCK_FLOOR_RESPONSE)

    agent = _make_agent(db_session, mock_vision)
    result = await agent.execute(ctx)

    assert result["room_count"] == 3
    assert result["floor_count"] == 1


@pytest.mark.asyncio
async def test_floorplan_agent_filename_fallback(db_session):
    """Asset named 'floorplan.jpg' with NO VisionResult is still detected
    via the filename heuristic fallback."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "600 Filename Fallback Ave"},
        metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    floorplan = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/floorplan.jpg",
        file_hash="fnfb01", state="ingested",
    )
    db_session.add(floorplan)
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    mock_vision = MagicMock()
    mock_vision.analyze_with_prompt_multi = AsyncMock(return_value=MOCK_FLOOR_RESPONSE)

    agent = _make_agent(db_session, mock_vision)
    result = await agent.execute(ctx)

    assert result["room_count"] == 3


@pytest.mark.asyncio
async def test_floorplan_agent_handles_multiple_floors(db_session):
    """Two floorplan assets produce a scene with floors[] length 2,
    and labels/levels come from the vision response for each call."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "700 Multi Floor Way"},
        metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    fp1 = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/floor1.jpg",
        file_hash="mf001", state="ingested",
    )
    fp2 = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/basement.jpg",
        file_hash="mf002", state="ingested",
    )
    db_session.add_all([fp1, fp2])
    await db_session.flush()

    for a in (fp1, fp2):
        db_session.add(VisionResult(
            asset_id=a.id, tier=1, room_label="floorplan",
            quality_score=50, commercial_score=0, hero_candidate=False,
        ))
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    mock_vision = MagicMock()
    responses = iter([
        _floor_response("First Floor", 1),
        _floor_response("Basement", -1),
    ])
    mock_vision.analyze_with_prompt_multi = AsyncMock(
        side_effect=lambda **kwargs: next(responses)
    )

    agent = _make_agent(db_session, mock_vision)
    result = await agent.execute(ctx)

    assert result["floor_count"] == 2
    assert result["room_count"] == 6  # 3 rooms * 2 floors

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    floors = scenes[0].scene_json["floors"]
    assert len(floors) == 2
    # Sorted by level ascending: basement (-1) first, then first floor (1)
    assert floors[0]["level"] == -1
    assert floors[0]["floor_label"] == "Basement"
    assert floors[1]["level"] == 1
    assert floors[1]["floor_label"] == "First Floor"


def test_dollhouse_prompt_exists():
    assert "floor_label" in FLOORPLAN_DOLLHOUSE_PROMPT
    assert "furniture" in FLOORPLAN_DOLLHOUSE_PROMPT
    assert "wall_color" in FLOORPLAN_DOLLHOUSE_PROMPT
    assert "JSON" in FLOORPLAN_DOLLHOUSE_PROMPT
