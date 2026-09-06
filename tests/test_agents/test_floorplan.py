# tests/test_agents/test_floorplan.py
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.floorplan import (
    FLOORPLAN_DOLLHOUSE_PROMPT,
    FloorplanAgent,
    FloorplanDoor,
    FloorplanFurniture,
    FloorplanRoom,
    FloorplanScene,
    FloorplanWindow,
)
from listingjet.models.asset import Asset
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing, ListingState
from listingjet.models.vision_result import VisionResult
from listingjet.providers.mock import MockClaudeClient
from tests.test_agents.conftest import make_session_factory


def _fake_storage():
    """Stub storage that turns an S3 key into a fake HTTP URL."""
    storage = MagicMock()
    storage.presigned_url = MagicMock(
        side_effect=lambda key, expires_in=3600: f"https://fake.example/{key}"
    )
    return storage


@pytest.fixture(autouse=True)
def patch_storage():
    """Safety net: mock the module-level get_storage() so any code path
    that falls through to the default storage still avoids boto3."""
    mock = MagicMock()
    mock.presigned_url.side_effect = lambda key, **kw: f"https://s3.example.com/{key}?signed=1"
    with patch("listingjet.agents.floorplan.get_storage", return_value=mock):
        yield mock


def test_dollhouse_scene_model_exists():
    from listingjet.models.dollhouse_scene import DollhouseScene
    assert hasattr(DollhouseScene, "listing_id")
    assert hasattr(DollhouseScene, "scene_json")
    assert hasattr(DollhouseScene, "room_count")


def _floor_scene(floor_label="First Floor", level=1) -> FloorplanScene:
    return FloorplanScene(
        floor_label=floor_label,
        level=level,
        structure="main_house",
        overall_width_meters=12.0,
        overall_height_meters=9.0,
        wall_height_meters=2.7,
        rooms=[
            FloorplanRoom(
                label="living_room",
                polygon=[[0.0, 0.0], [0.5, 0.0], [0.5, 0.4], [0.0, 0.4]],
                width_meters=6.0,
                height_meters=4.5,
                doors=[FloorplanDoor(wall="south", position=0.5)],
                windows=[FloorplanWindow(wall="east", position=0.3)],
                wall_color="#E8E2D0",
                flooring="hardwood",
                decor_tags=["beige walls"],
                furniture=[
                    FloorplanFurniture(type="sectional", x=0.3, y=0.5, rotation_degrees=0),
                ],
            ),
            FloorplanRoom(
                label="kitchen",
                polygon=[[0.5, 0.0], [1.0, 0.0], [1.0, 0.4], [0.5, 0.4]],
                width_meters=5.0,
                height_meters=4.5,
                doors=[FloorplanDoor(wall="west", position=0.5)],
                windows=[],
                wall_color="#FFFFFF",
                flooring="tile",
                decor_tags=[],
                furniture=[
                    FloorplanFurniture(type="kitchen_island", x=0.5, y=0.5, rotation_degrees=0),
                ],
            ),
            FloorplanRoom(
                label="bedroom",
                polygon=[[0.0, 0.4], [0.5, 0.4], [0.5, 1.0], [0.0, 1.0]],
                width_meters=6.0,
                height_meters=5.0,
                doors=[FloorplanDoor(wall="north", position=0.3)],
                windows=[FloorplanWindow(wall="west", position=0.5)],
                wall_color="#D6CFC4",
                flooring="carpet",
                decor_tags=[],
                furniture=[
                    FloorplanFurniture(type="queen_bed", x=0.5, y=0.5, rotation_degrees=0),
                ],
            ),
        ],
    )


MOCK_FLOOR_SCENE = _floor_scene()


def _mock_claude(*scenes: FloorplanScene) -> MockClaudeClient:
    client = MockClaudeClient()
    client.responses[FloorplanScene] = list(scenes) if scenes else [MOCK_FLOOR_SCENE]
    return client


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
            tier=1, room_label=room, is_photo=True,
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
        tier=1, room_label="floorplan", is_photo=False,
        raw_labels={"room": "floorplan"},
        quality_score=50, commercial_score=0, hero_candidate=False,
    ))
    await db_session.flush()
    return listing, floorplan, photos


def _make_agent(db_session, mock_claude):
    return FloorplanAgent(
        claude=mock_claude,
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
    )


@pytest.mark.asyncio
async def test_floorplan_agent_creates_scene(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_claude = _mock_claude()
    agent = _make_agent(db_session, mock_claude)
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
async def test_floorplan_agent_calls_claude_with_expected_args(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_claude = _mock_claude()
    mock_claude.analyze_images = AsyncMockRecorder(mock_claude)
    agent = _make_agent(db_session, mock_claude)
    await agent.execute(ctx)

    assert mock_claude.analyze_images.calls, "analyze_images was never called"
    call = mock_claude.analyze_images.calls[0]
    assert call.kwargs["model"] == "claude-sonnet-5"
    assert call.kwargs["max_tokens"] == 8000
    assert call.kwargs["agent"] == "floorplan"
    image_urls = call.args[0]
    assert image_urls[0] == "https://fake.example/" + floorplan.file_path
    assert len(image_urls) <= 6


@pytest.mark.asyncio
async def test_floorplan_agent_matches_photos_to_rooms(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_claude = _mock_claude()
    agent = _make_agent(db_session, mock_claude)
    await agent.execute(ctx)

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    rooms = scenes[0].scene_json["floors"][0]["rooms"]
    rooms_with_photos = [r for r in rooms if r.get("best_photo_asset_id")]
    assert len(rooms_with_photos) == 3


@pytest.mark.asyncio
async def test_floorplan_agent_emits_event(db_session, listing_with_floorplan):
    listing, floorplan, photos = listing_with_floorplan
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    mock_claude = _mock_claude()
    agent = _make_agent(db_session, mock_claude)
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

    mock_claude = _mock_claude()
    agent = _make_agent(db_session, mock_claude)
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["room_count"] == 0
    assert result.get("skipped") is True


@pytest.mark.asyncio
async def test_floorplan_agent_detects_via_vision(db_session):
    """Asset with a UUID-like filename (no 'floorplan' in path) is still detected
    when VisionResult tags it is_photo=False / raw_labels room=floorplan."""
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
        is_photo=False, raw_labels={"room": "floorplan"},
        quality_score=50, commercial_score=0, hero_candidate=False,
    ))
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    mock_claude = _mock_claude()
    agent = _make_agent(db_session, mock_claude)
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
    mock_claude = _mock_claude()
    agent = _make_agent(db_session, mock_claude)
    result = await agent.execute(ctx)

    assert result["room_count"] == 3


@pytest.mark.asyncio
async def test_floorplan_agent_handles_multiple_floors(db_session):
    """Two floorplan assets produce a scene with floors[] length 2,
    and labels/levels come from the Claude response for each call."""
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
            is_photo=False, raw_labels={"room": "floorplan"},
            quality_score=50, commercial_score=0, hero_candidate=False,
        ))
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    mock_claude = _mock_claude(
        _floor_scene("First Floor", 1),
        _floor_scene("Basement", -1),
    )

    agent = _make_agent(db_session, mock_claude)
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


@pytest.mark.asyncio
async def test_build_best_photo_map_skips_non_photo_vision_results(db_session, listing_with_floorplan):
    """A document/screenshot (is_photo=False) tier-1 row must never win a
    room's best-photo slot, even with a higher quality_score than the real
    photo for that room (e.g. an inspection PDF page mislabeled 'kitchen')."""
    listing, floorplan, photos = listing_with_floorplan

    doc_asset = Asset(
        tenant_id=listing.tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/inspection_doc.jpg",
        file_hash="doc001", state="ingested",
    )
    db_session.add(doc_asset)
    await db_session.flush()
    db_session.add(VisionResult(
        asset_id=doc_asset.id,
        tier=1, room_label="kitchen", is_photo=False,
        raw_labels={"room": "document"},
        quality_score=99, commercial_score=0, hero_candidate=False,
    ))
    await db_session.flush()

    all_assets = [*photos, floorplan, doc_asset]
    agent = _make_agent(db_session, _mock_claude())
    best = await agent._build_best_photo_map(db_session, all_assets)

    kitchen_asset_id, kitchen_quality = best["kitchen"]
    assert kitchen_asset_id != doc_asset.id
    assert kitchen_quality != 99


def test_dollhouse_prompt_exists():
    assert "floor_label" in FLOORPLAN_DOLLHOUSE_PROMPT
    assert "furniture" in FLOORPLAN_DOLLHOUSE_PROMPT
    assert "wall_color" in FLOORPLAN_DOLLHOUSE_PROMPT
    assert "JSON" in FLOORPLAN_DOLLHOUSE_PROMPT


class _Call:
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs


class AsyncMockRecorder:
    """Wraps MockClaudeClient.analyze_images to record call args/kwargs
    while still delegating to the real mock behavior."""

    def __init__(self, mock_claude: MockClaudeClient):
        self._mock_claude = mock_claude
        self._orig = MockClaudeClient.analyze_images.__get__(mock_claude)
        self.calls: list[_Call] = []

    async def __call__(self, *args, **kwargs):
        self.calls.append(_Call(args, kwargs))
        return await self._orig(*args, **kwargs)
