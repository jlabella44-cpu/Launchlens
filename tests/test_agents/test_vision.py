# tests/test_agents/test_vision.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.vision import VisionAgent
from listingjet.models.vision_result import VisionResult
from listingjet.providers.base import VisionLabel
from tests.test_agents.conftest import make_session_factory


def _mock_storage():
    storage = MagicMock()
    storage.presigned_url.side_effect = lambda key, **kw: f"https://s3.example.com/{key}?signed=1"
    return storage


@pytest.fixture(autouse=True)
def patch_storage():
    mock = _mock_storage()
    with patch("listingjet.agents.vision.get_storage", return_value=mock):
        yield mock


def make_mock_vision_provider(labels):
    provider = MagicMock()
    provider.analyze = AsyncMock(return_value=labels)
    return provider


@pytest.mark.asyncio
async def test_tier1_writes_vision_result_per_asset(db_session, listing, assets):
    for a in assets:
        a.state = "ingested"
    await db_session.flush()

    labels = [
        VisionLabel(name="living room", confidence=0.95, category="room"),
        VisionLabel(name="hardwood", confidence=0.88, category="feature"),
        VisionLabel(name="natural light", confidence=0.82, category="quality"),
    ]
    provider = make_mock_vision_provider(labels)
    agent = VisionAgent(
        vision_provider=provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.run_tier1(ctx)

    assert result == 3  # one VisionResult per asset
    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert len(rows) == 3
    assert all(r.tier == 1 for r in rows)
    assert all(r.room_label == "living_room" for r in rows)
    assert all(r.quality_score == 95 for r in rows)  # int(0.95 * 100)


@pytest.mark.asyncio
async def test_tier1_sets_hero_candidate_on_high_quality(db_session, listing, assets):
    for a in assets:
        a.state = "ingested"
    await db_session.flush()

    labels = [
        VisionLabel(name="building exterior", confidence=0.92, category="room"),
        VisionLabel(name="natural light", confidence=0.90, category="quality"),
        VisionLabel(name="hardwood", confidence=0.85, category="feature"),
        VisionLabel(name="stainless steel", confidence=0.80, category="feature"),
    ]
    provider = make_mock_vision_provider(labels)
    agent = VisionAgent(vision_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.run_tier1(ctx)

    rows = (await db_session.execute(select(VisionResult))).scalars().all()
    assert all(r.hero_candidate is True for r in rows)


@pytest.mark.asyncio
async def test_tier1_emits_event(db_session, listing, assets):
    for a in assets:
        a.state = "ingested"
    await db_session.flush()

    provider = make_mock_vision_provider([VisionLabel(name="kitchen", confidence=0.80, category="room")])
    agent = VisionAgent(vision_provider=provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.run_tier1(ctx)
    await db_session.flush()

    from listingjet.models.outbox import Outbox
    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "vision.tier1.completed")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].payload["asset_count"] == 3


@pytest.fixture
async def tier1_results(db_session, listing, assets):
    """Pre-populate Tier 1 VisionResults for 3 hero candidates."""
    for a in assets:
        a.state = "ingested"
        db_session.add(VisionResult(
            asset_id=a.id,
            tier=1,
            room_label="living_room",
            is_interior=True,
            quality_score=85,
            commercial_score=60,
            hero_candidate=True,
            raw_labels={},
            model_used="google-vision-v1",
        ))
    await db_session.flush()


@pytest.mark.asyncio
async def test_tier2_creates_results_for_hero_candidates(db_session, listing, assets, tier1_results):
    gpt_labels = [
        VisionLabel(name="primary exterior", confidence=0.95, category="shot_type"),
        VisionLabel(name="golden hour", confidence=0.88, category="quality"),
    ]
    gpt_provider = MagicMock()
    gpt_provider.analyze = AsyncMock(return_value=gpt_labels)

    agent = VisionAgent(
        vision_provider=gpt_provider,
        session_factory=make_session_factory(db_session),
    )
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    count = await agent.run_tier2(ctx)

    assert count == 3  # one Tier 2 result per hero candidate
    tier2_rows = (
        await db_session.execute(
            select(VisionResult).where(VisionResult.tier == 2)
        )
    ).scalars().all()
    assert len(tier2_rows) == 3
    assert all(r.model_used == "gpt-4o" for r in tier2_rows)


@pytest.mark.asyncio
async def test_tier2_skips_if_no_hero_candidates(db_session, listing, assets):
    """If no Tier 1 hero candidates, Tier 2 should be a no-op."""
    for a in assets:
        a.state = "ingested"
        db_session.add(VisionResult(
            asset_id=a.id,
            tier=1,
            room_label="bedroom",
            is_interior=True,
            quality_score=50,
            commercial_score=20,
            hero_candidate=False,
            raw_labels={},
            model_used="google-vision-v1",
        ))
    await db_session.flush()

    gpt_provider = MagicMock()
    gpt_provider.analyze = AsyncMock(return_value=[])
    agent = VisionAgent(vision_provider=gpt_provider, session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    count = await agent.run_tier2(ctx)

    assert count == 0
    assert gpt_provider.analyze.call_count == 0
