import uuid
from unittest.mock import MagicMock

import pytest
from PIL import Image
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.video_baseline import VideoBaselineAgent, select_baseline_photos
from listingjet.models.asset import Asset
from listingjet.models.brand_kit import BrandKit
from listingjet.models.listing import Listing, ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult
from listingjet.services.video_stitcher import VideoStitcher, probe_duration, probe_size
from tests.test_agents.conftest import make_session_factory

pytestmark = pytest.mark.ffmpeg


def _make_png_bytes(color=(120, 140, 160), size=(320, 180)) -> bytes:
    import io
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def make_storage_mock():
    """A storage mock whose download() returns a Pillow PNG per key and whose
    upload_bytes() records the key + bytes it was given."""
    storage = MagicMock()
    storage.download = MagicMock(side_effect=lambda key: _make_png_bytes())
    uploads: dict[str, bytes] = {}

    def _upload_bytes(data, key, content_type):
        uploads[key] = data
        return key

    storage.upload_bytes = MagicMock(side_effect=_upload_bytes)
    storage.uploads = uploads
    return storage


async def _make_listing(db_session, tenant_id=None):
    listing = Listing(
        tenant_id=tenant_id or uuid.uuid4(),
        address={"street": "42 Baseline Ave"}, metadata_={},
        state=ListingState.APPROVED,
    )
    db_session.add(listing)
    await db_session.flush()
    return listing


async def _package_asset(db_session, listing, position, *, room="living_room", is_photo=True, filename=None):
    asset = Asset(
        listing_id=listing.id,
        tenant_id=listing.tenant_id,
        file_path=filename or f"s3://bucket/listing/{listing.id}/photo_{position}.jpg",
        file_hash=f"hash{position}",
        state="uploaded",
    )
    db_session.add(asset)
    await db_session.flush()

    vr = VisionResult(
        asset_id=asset.id, tier=1, room_label=room, is_photo=is_photo,
        hero_score=80, quality_score=80,
    )
    db_session.add(vr)

    ps = PackageSelection(
        tenant_id=listing.tenant_id, listing_id=listing.id, asset_id=asset.id,
        channel="video", position=position,
    )
    db_session.add(ps)
    await db_session.flush()
    return asset, vr, ps


@pytest.mark.asyncio
async def test_builds_tour_from_packaged_photos(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")
    # a non-photo document mixed into the package — must be skipped
    await _package_asset(db_session, listing, 2, room="document", is_photo=False)
    await _package_asset(db_session, listing, 3, room="primary_bedroom")

    storage = make_storage_mock()
    agent = VideoBaselineAgent(
        storage=storage, session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["status"] == "ready"
    assert result["clip_count"] == 3
    expected_key = f"videos/{listing.id}/tour.mp4"
    assert result["s3_key"] == expected_key
    assert expected_key in storage.uploads

    video_bytes = storage.uploads[expected_key]
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        import os
        p = os.path.join(tmp, "out.mp4")
        with open(p, "wb") as f:
            f.write(video_bytes)
        duration = probe_duration(p)

    expected_duration = 3 * 3.0 - 2 * 0.5 + 5  # 3 ken-burns clips crossfaded + end card
    assert abs(duration - expected_duration) < 0.3

    rows = (await db_session.execute(
        select(VideoAsset).where(VideoAsset.listing_id == listing.id)
    )).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.video_type == "tour"
    assert row.status == "ready"
    assert row.chapters == [
        {"time": 0, "label": "exterior"},
        {"time": 2, "label": "kitchen"},
        {"time": 5, "label": "primary_bedroom"},
    ]
    assert row.metadata_["tier"] == "baseline"
    assert len(row.metadata_["clips"]) == 3
    assert all(c["source"] == "ken_burns" for c in row.metadata_["clips"])


@pytest.mark.asyncio
async def test_tour_keeps_requested_resolution(ffmpeg_available, db_session):
    """The end-card concat must not silently downscale the reel: VideoStitcher.stitch
    defaults to 1280x720, so the agent's width/height have to reach it."""
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    storage = make_storage_mock()
    agent = VideoBaselineAgent(
        storage=storage, session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    import os
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "out.mp4")
        with open(p, "wb") as f:
            f.write(storage.uploads[result["s3_key"]])
        assert probe_size(p) == (320, 180)


@pytest.mark.asyncio
async def test_skips_without_package(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    storage = make_storage_mock()
    agent = VideoBaselineAgent(storage=storage, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    result = await agent.execute(ctx)

    assert result == {"skipped": True, "reason": "no_packaged_photos"}
    storage.upload_bytes.assert_not_called()

    rows = (await db_session.execute(select(VideoAsset).where(VideoAsset.listing_id == listing.id))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_rerun_updates_same_row(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    storage = make_storage_mock()
    agent = VideoBaselineAgent(
        storage=storage, session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))

    first = await agent.execute(ctx)
    second = await agent.execute(ctx)

    rows = (await db_session.execute(select(VideoAsset).where(VideoAsset.listing_id == listing.id))).scalars().all()
    assert len(rows) == 1
    assert first["s3_key"] == second["s3_key"] == rows[0].s3_key


@pytest.mark.asyncio
async def test_caps_at_max_photos(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    for i in range(12):
        await _package_asset(db_session, listing, i, room="bedroom")

    storage = make_storage_mock()
    agent = VideoBaselineAgent(
        storage=storage, session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["clip_count"] == 10


@pytest.mark.asyncio
async def test_endcard_appended_when_brand_kit(ffmpeg_available, db_session):
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    brand_kit = BrandKit(
        tenant_id=listing.tenant_id, brokerage_name="Acme Realty",
        agent_name="Jane Doe", primary_color="#2563EB",
    )
    db_session.add(brand_kit)
    await db_session.flush()

    storage = make_storage_mock()
    agent = VideoBaselineAgent(
        storage=storage, session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    video_bytes = storage.uploads[result["s3_key"]]
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "out.mp4")
        with open(p, "wb") as f:
            f.write(video_bytes)
        duration = probe_duration(p)

    expected_duration = 2 * 3.0 - 1 * 0.5 + 5  # 2 ken-burns clips crossfaded + end card
    assert abs(duration - expected_duration) < 0.3


@pytest.mark.asyncio
async def test_endcard_appended_without_brand_kit(ffmpeg_available, db_session):
    """No BrandKit at all — the tour still gets a neutral default end card."""
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    storage = make_storage_mock()
    agent = VideoBaselineAgent(
        storage=storage, session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    video_bytes = storage.uploads[result["s3_key"]]
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "out.mp4")
        with open(p, "wb") as f:
            f.write(video_bytes)
        duration = probe_duration(p)

    expected_duration = 2 * 3.0 - 1 * 0.5 + 5  # same shape: end card always appended
    assert abs(duration - expected_duration) < 0.3


def test_select_baseline_photos_helper():
    """Unit-level check of the pure selection helper (no ffmpeg needed)."""
    listing_id = uuid.uuid4()

    def row(position, room, is_photo=True, filename=None):
        asset = Asset(
            id=uuid.uuid4(), listing_id=listing_id, tenant_id=uuid.uuid4(),
            file_path=filename or f"photo_{position}.jpg", file_hash=f"h{position}",
        )
        vr = VisionResult(asset_id=asset.id, tier=1, room_label=room, is_photo=is_photo)
        ps = PackageSelection(
            tenant_id=asset.tenant_id, listing_id=listing_id, asset_id=asset.id,
            channel="video", position=position,
        )
        return (ps, asset, vr)

    rows = [
        row(0, "exterior"),
        row(1, "floorplan"),  # excluded room label
        row(2, "document", is_photo=False),  # excluded is_photo
        row(3, "kitchen", filename="site_plan_3.jpg"),  # excluded filename marker
        row(4, "kitchen"),
    ]
    selected = select_baseline_photos(rows, max_photos=10)
    assert [a.file_path for a, _vr in selected] == ["photo_0.jpg", "photo_4.jpg"]


@pytest.mark.asyncio
async def test_injected_stitcher_is_used(ffmpeg_available, db_session):
    """A stitcher injected into the agent's constructor must actually be used
    by build_tour, not shadowed by a fresh VideoStitcher() built internally."""
    listing = await _make_listing(db_session)
    await _package_asset(db_session, listing, 0, room="exterior")
    await _package_asset(db_session, listing, 1, room="kitchen")

    storage = make_storage_mock()
    real_stitcher = VideoStitcher()
    spy_stitcher = MagicMock(wraps=real_stitcher)
    spy_stitcher.stitch_xfade = MagicMock(wraps=real_stitcher.stitch_xfade)

    agent = VideoBaselineAgent(
        storage=storage, stitcher=spy_stitcher,
        session_factory=make_session_factory(db_session),
        width=320, height=180,
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    spy_stitcher.stitch_xfade.assert_called_once()
    assert result["status"] == "ready"

    video_bytes = storage.uploads[result["s3_key"]]
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "out.mp4")
        with open(p, "wb") as f:
            f.write(video_bytes)
        duration = probe_duration(p)

    expected_duration = 2 * 3.0 - 1 * 0.5 + 5
    assert abs(duration - expected_duration) < 0.3
