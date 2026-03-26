# tests/test_agents/test_vision.py
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from launchlens.agents.vision import VisionAgent
from launchlens.agents.base import AgentContext
from launchlens.models.vision_result import VisionResult
from launchlens.providers.base import VisionLabel
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


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

    from launchlens.models.outbox import Outbox
    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "vision.tier1.completed")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].payload["asset_count"] == 3
