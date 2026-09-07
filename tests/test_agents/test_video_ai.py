import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.video_ai import VideoAIAgent
from listingjet.config import settings
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult
from listingjet.providers.mock import MockRunwayClient
from listingjet.providers.runway import RunwayError
from listingjet.services.video_stitcher import probe_size
from tests.test_agents.conftest import make_session_factory
from tests.test_agents.test_video_baseline import make_storage_mock


async def _make_listing(db_session, tenant_id=None):
    listing = Listing(
        tenant_id=tenant_id or uuid.uuid4(),
        address={"street": "42 Runway Ave"},
        metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


async def _package_asset(
    db_session, listing, position, *, room="living_room", hero_score=80, is_photo=True
):
    asset = Asset(
        listing_id=listing.id,
        tenant_id=listing.tenant_id,
        file_path=f"s3://bucket/listing/{listing.id}/photo_{position}.jpg",
        file_hash=f"hash{position}",
        state="uploaded",
    )
    db_session.add(asset)
    await db_session.flush()

    vr = VisionResult(
        asset_id=asset.id, tier=1, room_label=room, is_photo=is_photo,
        hero_score=hero_score, quality_score=hero_score,
    )
    db_session.add(vr)
    db_session.add(PackageSelection(
        tenant_id=listing.tenant_id, listing_id=listing.id, asset_id=asset.id,
        channel="video", position=position,
    ))
    await db_session.flush()
    return asset


def _rows_from(pairs):
    """Build (PackageSelection, Asset, VisionResult) tuples in package order."""
    listing_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    rows = []
    for position, (room, hero) in enumerate(pairs):
        asset = Asset(
            id=uuid.uuid4(), listing_id=listing_id, tenant_id=tenant_id,
            file_path=f"photo_{position}.jpg", file_hash=f"h{position}",
        )
        vr = VisionResult(
            asset_id=asset.id, tier=1, room_label=room, is_photo=True,
            hero_score=hero, quality_score=hero,
        )
        ps = PackageSelection(
            tenant_id=tenant_id, listing_id=listing_id, asset_id=asset.id,
            channel="video", position=position,
        )
        rows.append((ps, asset, vr))
    return rows


def test_select_shots_order_and_cap():
    rows = _rows_from([
        ("exterior", 60),
        ("exterior", 95),          # the better exterior — must be the opener
        ("drone", 50),
        ("kitchen", 70),
        ("primary_bedroom", 70),
        ("living_room", 70),
        ("bathroom", 70),
        ("entryway", 70),
        ("garage", 70),
    ])

    agent = VideoAIAgent(runway=MockRunwayClient(), storage=make_storage_mock(), max_shots=6)
    shots = agent.select_shots(rows)

    assert len(shots) == 6
    assert [s.kind for s in shots] == ["exterior", "drone", "interior", "interior", "interior", "interior"]
    assert shots[0].asset.file_path == "photo_1.jpg"  # highest hero_score exterior
    assert shots[1].room == "drone"
    # interiors follow WALKTHROUGH_ORDER: entryway, living_room, kitchen, primary_bedroom
    assert [s.room for s in shots[2:]] == ["entryway", "living_room", "kitchen", "primary_bedroom"]


def test_model_routing():
    agent = VideoAIAgent(runway=MockRunwayClient(), storage=make_storage_mock())
    assert agent.model_for("exterior") == (settings.runway_exterior_model, 6, False)
    assert agent.model_for("drone") == (settings.runway_exterior_model, 6, False)
    assert agent.model_for("interior") == (settings.runway_interior_model, 5, None)


@pytest.mark.ffmpeg
@pytest.mark.asyncio
async def test_generates_and_stitches(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")
    await _package_asset(db_session, listing, 2, room="primary_bedroom")

    runway = MockRunwayClient()
    storage = make_storage_mock()
    agent = VideoAIAgent(
        runway=runway, storage=storage,
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["status"] == "ready"
    assert result["runway_clips"] == 3
    assert result["fallback_clips"] == 0

    models = [s["model"] for s in runway.submitted]
    assert models == [
        settings.runway_exterior_model,
        settings.runway_interior_model,
        settings.runway_interior_model,
    ]
    assert [s["duration"] for s in runway.submitted] == [6, 5, 5]

    expected_key = f"videos/{listing.id}/tour.mp4"
    assert result["s3_key"] == expected_key
    assert expected_key in storage.uploads

    # 1 exterior @ 6s on veo3.1_fast + 2 interiors @ 5s on gen4_turbo
    from listingjet.config.ai_rates import VIDEO_SECOND_RATES
    expected_cost = (
        6 * VIDEO_SECOND_RATES[settings.runway_exterior_model]
        + 2 * 5 * VIDEO_SECOND_RATES[settings.runway_interior_model]
    )
    assert result["cost_usd"] == pytest.approx(expected_cost)
    assert result["cost_usd"] == pytest.approx(1.10)

    row = (await db_session.execute(
        select(VideoAsset).where(VideoAsset.listing_id == listing.id)
    )).scalars().one()
    assert row.status == "ready"
    assert row.metadata_["tier"] == "ai"
    assert len(row.metadata_["runway_tasks"]) == 3
    assert len(row.metadata_["clips"]) == 3
    assert all(c["source"] == "runway" for c in row.metadata_["clips"])
    assert all(c["model"] for c in row.metadata_["clips"])
    assert [c["label"] for c in row.chapters] == ["exterior", "kitchen", "primary_bedroom"]

    # the end-card concat must not downscale the reel to VideoStitcher's 1280x720 default
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "out.mp4")
        with open(p, "wb") as f:
            f.write(storage.uploads[expected_key])
        assert probe_size(p) == (320, 180)


@pytest.mark.ffmpeg
@pytest.mark.asyncio
async def test_expired_output_url_falls_back_to_ken_burns(ffmpeg_available, db_session):
    """A dead download (expired output URL) degrades that one shot, like a dead task."""
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    runway = MockRunwayClient()
    real_download = runway.download

    async def flaky_download(url):
        # the exterior is submitted first, so it holds mock-task-1
        if url.endswith("mock-task-1"):
            raise RunwayError("Runway download failed: 403 expired")
        return await real_download(url)

    runway.download = flaky_download

    storage = make_storage_mock()
    agent = VideoAIAgent(
        runway=runway, storage=storage,
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["status"] == "ready"
    assert result["runway_clips"] == 1
    assert result["fallback_clips"] == 1

    row = (await db_session.execute(
        select(VideoAsset).where(VideoAsset.listing_id == listing.id)
    )).scalars().one()
    clips = row.metadata_["clips"]
    assert clips[0]["source"] == "ken_burns"
    assert clips[1]["source"] == "runway"


@pytest.mark.ffmpeg
@pytest.mark.asyncio
async def test_endcard_uses_tenant_brand_kit(ffmpeg_available, db_session, monkeypatch):
    """The paid tier must brand its end card, not fall back to the neutral default."""
    import listingjet.agents.video_ai as video_ai_module
    from listingjet.services.endcard import generate_endcard

    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")
    db_session.add(BrandKit(
        tenant_id=listing.tenant_id, brokerage_name="Acme Realty",
        agent_name="Jane Doe", primary_color="#FF00AA",
    ))
    await db_session.flush()

    spy = MagicMock(side_effect=generate_endcard)
    monkeypatch.setattr(video_ai_module, "generate_endcard", spy)

    agent = VideoAIAgent(
        runway=MockRunwayClient(), storage=make_storage_mock(),
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["status"] == "ready"
    spy.assert_called_once_with(
        brokerage_name="Acme Realty", agent_name="Jane Doe", primary_color="#FF00AA",
    )


@pytest.mark.ffmpeg
@pytest.mark.asyncio
async def test_failed_shot_falls_back_to_ken_burns(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    runway = MockRunwayClient()
    runway.fail_models = {settings.runway_exterior_model}
    storage = make_storage_mock()
    agent = VideoAIAgent(
        runway=runway, storage=storage,
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["status"] == "ready"
    assert result["runway_clips"] == 1
    assert result["fallback_clips"] == 1
    assert f"videos/{listing.id}/tour.mp4" in storage.uploads

    row = (await db_session.execute(
        select(VideoAsset).where(VideoAsset.listing_id == listing.id)
    )).scalars().one()
    clips = row.metadata_["clips"]
    assert clips[0]["source"] == "ken_burns"
    assert clips[0]["model"] is None
    assert clips[1]["source"] == "runway"
    # only the succeeded Runway clip is billed
    from listingjet.config.ai_rates import VIDEO_SECOND_RATES
    assert result["cost_usd"] == pytest.approx(5 * VIDEO_SECOND_RATES[settings.runway_interior_model])


@pytest.mark.asyncio
async def test_unhandled_render_error_propagates(db_session, monkeypatch):
    """`_render_shot` swallows the failures it knows how to degrade (Ken
    Burns fallback); anything else it raises is genuinely unhandled and must
    come back out of `gather(..., return_exceptions=True)` and out of
    `execute` rather than being silently absorbed."""
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    runway = MockRunwayClient()
    storage = make_storage_mock()
    agent = VideoAIAgent(
        runway=runway, storage=storage,
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )

    async def boom(*args, **kwargs):
        raise ValueError("render exploded")

    monkeypatch.setattr(agent, "_render_shot", boom)

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    with pytest.raises(ValueError, match="render exploded"):
        await agent.execute(ctx)


@pytest.mark.ffmpeg
@pytest.mark.asyncio
async def test_resume_polls_existing_tasks(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    asset_a = await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")
    await _package_asset(db_session, listing, 2, room="primary_bedroom")

    db_session.add(VideoAsset(
        tenant_id=listing.tenant_id, listing_id=listing.id,
        s3_key=f"videos/{listing.id}/tour.mp4", video_type="tour",
        duration_seconds=0, status="processing", clip_count=0, chapters=[],
        metadata_={"tier": "ai", "clips": [], "runway_tasks": {str(asset_a.id): "mock-task-99"}},
    ))
    await db_session.flush()

    runway = MockRunwayClient()
    storage = make_storage_mock()
    agent = VideoAIAgent(
        runway=runway, storage=storage,
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["status"] == "ready"
    assert len(runway.submitted) == 2  # asset_a was NOT resubmitted
    assert all(s["model"] == settings.runway_interior_model for s in runway.submitted)

    row = (await db_session.execute(
        select(VideoAsset).where(VideoAsset.listing_id == listing.id)
    )).scalars().one()
    assert row.metadata_["runway_tasks"][str(asset_a.id)] == "mock-task-99"
    assert len(row.metadata_["runway_tasks"]) == 3


@pytest.mark.asyncio
async def test_task_ids_persisted_before_polling(db_session):
    listing = await _make_listing(db_session)
    a0 = await _package_asset(db_session, listing, 0, room="exterior")
    a1 = await _package_asset(db_session, listing, 1, room="kitchen")

    runway = MockRunwayClient()

    async def _boom(task_id, *, timeout_s=900.0, poll_s=5.0):
        raise RuntimeError("polling exploded")

    runway.wait = _boom

    storage = make_storage_mock()
    agent = VideoAIAgent(
        runway=runway, storage=storage,
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    with pytest.raises(RuntimeError, match="polling exploded"):
        await agent.execute(ctx)

    row = (await db_session.execute(
        select(VideoAsset).where(VideoAsset.listing_id == listing.id)
    )).scalars().one()
    tasks = row.metadata_["runway_tasks"]
    assert set(tasks) == {str(a0.id), str(a1.id)}
    assert all(t.startswith("mock-task-") for t in tasks.values())
