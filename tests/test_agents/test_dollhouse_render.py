import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.dollhouse_render import DollhouseRenderAgent
from listingjet.models.asset import Asset
from listingjet.models.dollhouse_scene import DollhouseScene
from listingjet.models.listing import Listing, ListingState
from listingjet.providers.openai_dollhouse import DollhouseRenderError
from tests.test_agents.conftest import make_session_factory


def _scene_json(
    floorplan_asset_id: uuid.UUID,
    living_room_photo_id: uuid.UUID,
    kitchen_photo_id: uuid.UUID,
) -> dict:
    return {
        "version": 2,
        "wall_height_meters": 2.7,
        "floors": [
            {
                "floor_label": "First Floor",
                "level": 1,
                "structure": "main_house",
                "dimensions": {"width_meters": 12.0, "height_meters": 9.0},
                "wall_height_meters": 2.7,
                "source_floorplan_asset_id": str(floorplan_asset_id),
                "rooms": [
                    {
                        "label": "living_room",
                        "polygon": [[0, 0], [0.5, 0], [0.5, 0.4], [0, 0.4]],
                        "width_meters": 6.0, "height_meters": 4.5,
                        "doors": [], "windows": [],
                        "wall_color": "#E8E2D0",
                        "flooring": "hardwood",
                        "decor_tags": [],
                        "furniture": [],
                        "best_photo_asset_id": str(living_room_photo_id),
                    },
                    {
                        "label": "kitchen",
                        "polygon": [[0.5, 0], [1, 0], [1, 0.4], [0.5, 0.4]],
                        "width_meters": 5.0, "height_meters": 4.5,
                        "doors": [], "windows": [],
                        "wall_color": "#FFFFFF",
                        "flooring": "tile",
                        "decor_tags": [],
                        "furniture": [],
                        "best_photo_asset_id": str(kitchen_photo_id),
                    },
                ],
            }
        ],
    }


def _fake_storage():
    storage = MagicMock()
    storage.presigned_url = MagicMock(
        side_effect=lambda key, expires_in=3600: f"https://fake.example/{key}"
    )
    storage.upload = MagicMock(
        side_effect=lambda key, data, content_type: key
    )
    return storage


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

    floorplan = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/floorplan.jpg",
        file_hash="fp01", state="ingested",
    )
    living = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/living.jpg",
        file_hash="lr01", state="ingested",
    )
    kitchen = Asset(
        tenant_id=tenant_id, listing_id=listing.id,
        file_path=f"listings/{listing.id}/kitchen.jpg",
        file_hash="kt01", state="ingested",
    )
    db_session.add_all([floorplan, living, kitchen])
    await db_session.flush()

    scene = DollhouseScene(
        tenant_id=tenant_id,
        listing_id=listing.id,
        scene_json=_scene_json(floorplan.id, living.id, kitchen.id),
        room_count=2,
        floorplan_asset_id=floorplan.id,
    )
    db_session.add(scene)
    await db_session.flush()
    return listing, scene, floorplan, living, kitchen


@pytest.mark.asyncio
async def test_dollhouse_render_agent_uploads_png(db_session, listing_with_scene):
    listing, _scene, floorplan, living, kitchen = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    storage = _fake_storage()
    stub_png = b"\x89PNG\r\n\x1a\n" + b"0" * 512

    captured: dict = {}

    def stub_render(floorplan_url: str, room_photo_urls):
        captured["floorplan_url"] = floorplan_url
        captured["room_photo_urls"] = list(room_photo_urls)
        return stub_png

    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=storage,
        render_fn=stub_render,
    )

    result = await agent.execute(ctx)

    assert result["render_key"] == f"listings/{listing.id}/dollhouse.png"
    assert captured["floorplan_url"] == f"https://fake.example/{floorplan.file_path}"
    assert captured["room_photo_urls"] == [
        f"https://fake.example/{living.file_path}",
        f"https://fake.example/{kitchen.file_path}",
    ]

    storage.upload.assert_called_once()
    upload_kwargs = storage.upload.call_args.kwargs
    assert upload_kwargs["key"] == f"listings/{listing.id}/dollhouse.png"
    assert upload_kwargs["data"] == stub_png
    assert upload_kwargs["content_type"] == "image/png"

    scenes = (await db_session.execute(select(DollhouseScene))).scalars().all()
    assert scenes[0].scene_json["render_key"] == f"listings/{listing.id}/dollhouse.png"


@pytest.mark.asyncio
async def test_dollhouse_render_agent_accepts_async_render_fn(db_session, listing_with_scene):
    listing, *_ = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    stub_png = b"\x89PNG\r\n\x1a\n" + b"async" * 50

    async def async_render(_floorplan_url, _room_photo_urls):
        return stub_png

    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=async_render,
    )

    result = await agent.execute(ctx)
    assert result["render_key"] == f"listings/{listing.id}/dollhouse.png"


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
        render_fn=lambda *_args, **_kw: b"",
    )

    result = await agent.execute(ctx)
    assert result.get("skipped") is True
    assert "No dollhouse scene" in result.get("reason", "")


@pytest.mark.asyncio
async def test_dollhouse_render_agent_skips_when_no_floorplan_asset(db_session):
    """Scene exists but source_floorplan_asset_id points at nothing."""
    tenant_id = uuid.uuid4()
    listing = Listing(
        tenant_id=tenant_id,
        address={"street": "Orphan Scene Dr"},
        metadata_={}, state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()

    scene = DollhouseScene(
        tenant_id=tenant_id,
        listing_id=listing.id,
        scene_json={
            "version": 2,
            "wall_height_meters": 2.7,
            "floors": [
                {
                    "floor_label": "First Floor",
                    "level": 1,
                    "structure": "main_house",
                    "dimensions": {"width_meters": 10, "height_meters": 8},
                    "wall_height_meters": 2.7,
                    "source_floorplan_asset_id": None,
                    "rooms": [],
                }
            ],
        },
        room_count=0,
        floorplan_asset_id=None,
    )
    db_session.add(scene)
    await db_session.flush()

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=lambda *_args, **_kw: b"",
    )

    result = await agent.execute(ctx)
    assert result.get("skipped") is True
    assert "floorplan" in result.get("reason", "").lower()


@pytest.mark.asyncio
async def test_dollhouse_render_agent_skips_on_provider_error(db_session, listing_with_scene):
    listing, *_ = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    def boom(*_args, **_kw):
        raise DollhouseRenderError("content policy violation")

    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=boom,
    )

    result = await agent.execute(ctx)
    assert result.get("skipped") is True
    assert "content policy" in result.get("reason", "")


@pytest.mark.asyncio
async def test_dollhouse_render_agent_skips_on_unexpected_exception(db_session, listing_with_scene):
    listing, *_ = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    def crash(*_args, **_kw):
        raise RuntimeError("disk exploded")

    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=crash,
    )

    result = await agent.execute(ctx)
    assert result.get("skipped") is True
    assert "Render failed" in result.get("reason", "")


@pytest.mark.asyncio
async def test_dollhouse_render_agent_emits_event(db_session, listing_with_scene):
    listing, *_ = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    stub_png = b"\x89PNG\r\n\x1a\n" + b"x" * 128
    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        render_fn=lambda *_a, **_k: stub_png,
    )
    await agent.execute(ctx)

    from listingjet.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.event_type == "dollhouse.rendered")
    )).scalars().all()
    assert len(events) == 1
    assert events[0].payload["input_image_count"] == 3  # 1 floorplan + 2 room photos


@pytest.mark.asyncio
async def test_dollhouse_render_agent_uses_real_provider_when_no_render_fn(db_session, listing_with_scene):
    """When render_fn is not injected, the agent should call OpenAIDollhouseProvider.generate."""
    listing, *_ = listing_with_scene
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    fake_provider = MagicMock()
    fake_provider.generate = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"fake")

    agent = DollhouseRenderAgent(
        session_factory=make_session_factory(db_session),
        storage=_fake_storage(),
        provider=fake_provider,
    )

    result = await agent.execute(ctx)
    assert result["render_key"] == f"listings/{listing.id}/dollhouse.png"
    fake_provider.generate.assert_awaited_once()
    call_kwargs = fake_provider.generate.await_args.kwargs
    assert "floorplan_url" in call_kwargs
    assert "room_photo_urls" in call_kwargs
    assert len(call_kwargs["room_photo_urls"]) == 2
