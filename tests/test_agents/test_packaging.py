import pytest
import uuid
from launchlens.agents.packaging import PackagingAgent
from launchlens.agents.base import AgentContext
from launchlens.models.vision_result import VisionResult
from launchlens.models.package_selection import PackageSelection
from launchlens.models.listing import ListingState
from launchlens.services.weight_manager import WeightManager
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


async def _add_vr(db_session, asset_id, quality=80, commercial=60, hero=True, tier=1):
    vr = VisionResult(
        asset_id=asset_id,
        tier=tier,
        room_label="living_room",
        is_interior=True,
        quality_score=quality,
        commercial_score=commercial,
        hero_candidate=hero,
        raw_labels={},
        model_used="google-vision-v1",
    )
    db_session.add(vr)
    await db_session.flush()
    return vr


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

    # Give assets different quality scores so one is clearly best
    for i, asset in enumerate(assets):
        await _add_vr(db_session, asset.id, quality=80 - i*10, commercial=60, hero=(i == 0))

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

    for asset in assets:
        await _add_vr(db_session, asset.id)

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
    result = await agent.execute(ctx)

    rows = (await db_session.execute(select(PackageSelection))).scalars().all()
    assert len(rows) == 1
    # Top scorer should use Tier 2 score (95), so composite_score should be high
    assert rows[0].composite_score > 0.7
