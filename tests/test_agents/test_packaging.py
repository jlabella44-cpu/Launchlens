
import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.packaging import (
    REQUIRED_ROOMS,
    ROOM_MAX_SLOTS,
    PackagingAgent,
)
from listingjet.models.listing import ListingState
from listingjet.models.package_selection import PackageSelection
from listingjet.models.vision_result import VisionResult
from listingjet.services.weight_manager import WeightManager
from tests.test_agents.conftest import make_session_factory


async def _add_vr(db_session, asset_id, quality=80, commercial=60, hero=True, tier=1, room_label="living_room"):
    vr = VisionResult(
        asset_id=asset_id,
        tier=tier,
        room_label=room_label,
        is_interior=(room_label not in {None, "exterior", "garage", "pool", "backyard"}),
        quality_score=quality,
        commercial_score=commercial,
        hero_candidate=hero,
        raw_labels={},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()
    return vr


def _make_scored(room_label, quality=80, commercial=60, hero=False, asset_id=None):
    """Create a (score, asset_id, vr) tuple for unit-testing _select_diverse / _reorder_mls."""
    import uuid as _uuid
    aid = asset_id or _uuid.uuid4()
    vr = VisionResult(
        asset_id=aid,
        tier=1,
        room_label=room_label,
        is_interior=(room_label not in {None, "exterior", "garage", "pool", "backyard"}),
        quality_score=quality,
        commercial_score=commercial,
        hero_candidate=hero,
        raw_labels={},
        model_used="google-vision-v1",
    )
    wm = WeightManager()
    score = wm.score({"quality_score": quality, "commercial_score": commercial,
                      "hero_candidate": hero, "room_weight": 1.0})
    return (score, aid, vr)


def test_weight_manager_score_returns_float():
    wm = WeightManager()
    score = wm.score({"quality_score": 80, "commercial_score": 60,
                      "room_weight": 1.0, "hero_candidate": True})
    assert 0.0 <= score <= 1.0


def test_weight_manager_score_hero_scores_higher():
    wm = WeightManager()
    hero = wm.score({"quality_score": 80, "commercial_score": 60,
                     "room_weight": 1.0, "hero_candidate": True})
    non_hero = wm.score({"quality_score": 80, "commercial_score": 60,
                         "room_weight": 1.0, "hero_candidate": False})
    assert hero > non_hero


@pytest.mark.asyncio
async def test_packaging_selects_hero_asset(db_session, listing, assets):
    listing.state = ListingState.ANALYZING
    await db_session.flush()

    # Give assets different quality scores and room labels
    rooms = ["exterior", "kitchen", "living_room"]
    for i, asset in enumerate(assets):
        await _add_vr(db_session, asset.id, quality=80 - i*10, commercial=60, hero=(i == 0), room_label=rooms[i])

    agent = PackagingAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["total_selected"] == 3
    await db_session.refresh(listing)
    assert listing.state == ListingState.AWAITING_REVIEW


@pytest.mark.asyncio
async def test_packaging_writes_package_selection_rows(db_session, listing, assets):
    listing.state = ListingState.ANALYZING
    await db_session.flush()

    rooms = ["exterior", "kitchen", "living_room"]
    for i, asset in enumerate(assets):
        await _add_vr(db_session, asset.id, room_label=rooms[i])

    agent = PackagingAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    rows = (await db_session.execute(select(PackageSelection))).scalars().all()
    assert len(rows) == 3
    assert all(r.channel == "mls" for r in rows)
    assert all(r.selected_by == "ai" for r in rows)


@pytest.mark.asyncio
async def test_packaging_prefers_tier2_over_tier1(db_session, listing, assets):
    listing.state = ListingState.ANALYZING
    await db_session.flush()

    asset = assets[0]
    # Tier 1 low quality, Tier 2 high quality for same asset
    await _add_vr(db_session, asset.id, quality=40, tier=1, hero=False)
    await _add_vr(db_session, asset.id, quality=95, tier=2, hero=True)

    agent = PackagingAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    rows = (await db_session.execute(select(PackageSelection))).scalars().all()
    assert len(rows) == 1
    # Top scorer should use Tier 2 score (95), so composite_score should be high
    assert rows[0].composite_score > 0.7


# --- Diversity selection tests (unit tests on static methods) ---


def test_select_diverse_includes_required_rooms():
    """Required rooms (exterior, kitchen, living_room, bathroom) are included when available."""
    scored = [
        _make_scored("bedroom", quality=95),  # highest score
        _make_scored("bedroom", quality=90),
        _make_scored("bedroom", quality=85),
        _make_scored("exterior", quality=70),
        _make_scored("kitchen", quality=65),
        _make_scored("living_room", quality=60),
        _make_scored("bathroom", quality=55),
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = PackagingAgent._select_diverse(scored)
    rooms = {item[2].room_label for item in top}
    for req in REQUIRED_ROOMS:
        assert req in rooms, f"Required room '{req}' missing from selection"


def test_select_diverse_enforces_room_caps():
    """No more than ROOM_MAX_SLOTS bedrooms are selected."""
    scored = [_make_scored("bedroom", quality=90 - i) for i in range(10)]
    scored += [_make_scored("exterior", quality=70)]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = PackagingAgent._select_diverse(scored)
    bedroom_count = sum(1 for _, _, vr in top if vr.room_label == "bedroom")
    assert bedroom_count <= ROOM_MAX_SLOTS["bedroom"]


def test_select_diverse_excludes_laundry():
    """Laundry photos (max_slots=0) are never selected."""
    scored = [
        _make_scored("laundry", quality=95),  # high score but excluded
        _make_scored("exterior", quality=70),
        _make_scored("kitchen", quality=65),
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = PackagingAgent._select_diverse(scored)
    rooms = [item[2].room_label for item in top]
    assert "laundry" not in rooms


def test_select_diverse_filters_low_quality():
    """Photos below MIN_QUALITY_SCORE are excluded."""
    scored = [
        _make_scored("exterior", quality=10),  # below threshold
        _make_scored("kitchen", quality=15),    # below threshold
        _make_scored("living_room", quality=80),
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = PackagingAgent._select_diverse(scored)
    assert len(top) == 1
    assert top[0][2].room_label == "living_room"


def test_reorder_mls_exterior_first():
    """Hero photo (position 0) should be exterior when available."""
    scored = [
        _make_scored("bedroom", quality=95),    # highest score
        _make_scored("exterior", quality=70),    # lower score but should be hero
        _make_scored("kitchen", quality=65),
    ]
    reordered = PackagingAgent._reorder_mls(scored)
    assert reordered[0][2].room_label == "exterior"


def test_reorder_mls_follows_room_priority():
    """After hero, rooms should follow MLS priority order."""
    scored = [
        _make_scored("exterior", quality=70),
        _make_scored("bathroom", quality=85),
        _make_scored("kitchen", quality=65),
        _make_scored("living_room", quality=60),
    ]
    reordered = PackagingAgent._reorder_mls(scored)
    labels = [item[2].room_label for item in reordered]
    assert labels[0] == "exterior"
    # living_room before kitchen before bathroom in MLS order
    assert labels.index("living_room") < labels.index("kitchen")
    assert labels.index("kitchen") < labels.index("bathroom")
