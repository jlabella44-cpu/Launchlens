import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.dollhouse_render import DollhouseRenderAgent, _render_scene_to_png
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing, ListingState
from tests.test_agents.conftest import make_session_factory

SAMPLE_SCENE_JSON = {
    "version": 2,
    "wall_height_meters": 2.7,
    "floors": [
        {
            "floor_label": "First Floor",
            "level": 1,
            "structure": "main_house",
            "dimensions": {"width_meters": 12.0, "height_meters": 9.0},
            "wall_height_meters": 2.7,
            "source_floorplan_asset_id": "dummy",
            "rooms": [
                {
                    "label": "living_room",
                    "polygon": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.4], [0.0, 0.4]],
                    "width_meters": 6.0, "height_meters": 4.5,
                    "doors": [], "windows": [],
                    "wall_color": "#E8E2D0",
                    "flooring": "hardwood",
                    "decor_tags": [],
                    "furniture": [
                        {"type": "sectional", "x": 0.5, "y": 0.5, "rotation_degrees": 0},
                    ],
                },
                {
                    "label": "kitchen",
                    "polygon": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.4], [0.5, 0.4]],
                    "width_meters": 5.0, "height_meters": 4.5,
                    "doors": [], "windows": [],
                    "wall_color": "#FFFFFF",
                    "flooring": "tile",
                    "decor_tags": [],
                    "furniture": [
                        {"type": "kitchen_island", "x": 0.5, "y": 0.5, "rotation_degrees": 0},
                    ],
                },
            ],
        },
    ],
}


def _fake_storage():
    storage = MagicMock()
    storage.upload = MagicMock(
        side_effect=lambda key, data, content_type: key
    )
    return storage


def test_render_scene_to_png_returns_png_bytes():
    png = _render_scene_to_png(SAMPLE_SCENE_JSON)
    assert isinstance(png, (bytes, bytearray))
    assert len(png) > 1000
    # PNG magic number: 89 50 4E 47 0D 0A 1A 0A
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_scene_to_png_multi_floor():
    multi = {
        **SAMPLE_SCENE_JSON,
        "floors": [
            SAMPLE_SCENE_JSON["floors"][0],
            {
                "floor_label": "Basement",
                "level": -1,
                "structure": "main_house",
                "dimensions": {"width_meters": 12.0, "height_meters": 9.0},
                "wall_height_meters": 2.4,
                "source_floorplan_asset_id": "dummy2",
                "rooms": [
                    {
                        "label": "basement",
                        "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]],
                        "width_meters": 12.0, "height_meters": 9.0,
                        "doors": [], "windows": [],
                        "wall_color": None, "flooring": "concrete",
                        "decor_tags": [], "furniture": [],
                    }
                ],
            },
        ],
    }
    png = _render_scene_to_png(multi)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_scene_to_png_raises_on_no_floors():
    with pytest.raises(ValueError):
        _render_scene_to_png({"version": 2, "floors": []})


@pytest.fixture
async def listing_with_scene(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "400 Render Rd"},
        metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    scene = DollhouseScene(
        tenant_id=tenant_id,
        listing_id=listing.id,
        scene_json=SAMPLE_SCENE_JSON,
        room_count=2,
        floorplan_asset_id=None,
    )
    db_session.add(scene)
    await db_session.flush()
    return listing, scene


@pytest.mark.asyncio
async def test_dollhouse_render_agent_uploads_png(db_session, listing_with_scene):
    listing, scene = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    storage = _fake_storage()
    # Use a fast stub render function so the test doesn't spin up matplotlib.
    stub_png = b"\x89PNG\r\n\x1a\n" + b"0" * 512
    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=storage,
        render_fn=lambda _scene: stub_png,
    )

    result = await agent.execute(ctx)

    assert result["render_key"] == f"listings/{listing.id}/dollhouse.png"
    storage.upload.assert_called_once()
    upload_kwargs = storage.upload.call_args.kwargs
    assert upload_kwargs["key"] == f"listings/{listing.id}/dollhouse.png"
    assert upload_kwargs["data"] == stub_png
    assert upload_kwargs["content_type"] == "image/png"

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    assert scenes[0].scene_json["render_key"] == f"listings/{listing.id}/dollhouse.png"


@pytest.mark.asyncio
async def test_dollhouse_render_agent_skips_when_no_scene(db_session):
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "No Scene Ave"},
        metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=lambda _scene: b"",
    )

    result = await agent.execute(ctx)
    assert result.get("skipped") is True


@pytest.mark.asyncio
async def test_dollhouse_render_agent_skips_on_render_failure(db_session, listing_with_scene):
    listing, _scene = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    def _boom(_scene_json):
        raise RuntimeError("matplotlib broke")

    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=_boom,
    )

    result = await agent.execute(ctx)
    assert result.get("skipped") is True
    assert "Render failed" in result.get("reason", "")


@pytest.mark.asyncio
async def test_dollhouse_render_agent_emits_event(db_session, listing_with_scene):
    listing, _scene = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    stub_png = b"\x89PNG\r\n\x1a\n" + b"x" * 128
    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=lambda _scene: stub_png,
    )
    await agent.execute(ctx)

    from listingjet.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "dollhouse.rendered")
    )).scalars().all()
    assert len(events) == 1
