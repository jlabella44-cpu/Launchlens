import pytest
from sqlalchemy import select
from datetime import datetime, timezone

from launchlens.agents.learning import LearningAgent
from launchlens.agents.base import AgentContext
from launchlens.models.event import Event
from launchlens.models.learning_weight import LearningWeight
from tests.test_agents.conftest import make_session_factory


async def _add_override_event(db_session, listing, event_type, room_label="living_room"):
    ev = Event(
        event_type=event_type,
        payload={"room_label": room_label},
        tenant_id=listing.tenant_id,
        listing_id=listing.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(ev)
    await db_session.flush()


@pytest.mark.asyncio
async def test_learning_creates_weight_on_first_approval(db_session, listing, assets):
    await _add_override_event(db_session, listing, "package.override.approved", "living_room")

    agent = LearningAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["weights_updated"] == 1
    weights = (await db_session.execute(select(LearningWeight))).scalars().all()
    assert len(weights) == 1
    assert weights[0].room_label == "living_room"
    # approval should increase weight above 1.0 baseline
    assert weights[0].weight > 1.0


@pytest.mark.asyncio
async def test_learning_upserts_existing_weight(db_session, listing, assets):
    existing = LearningWeight(
        tenant_id=listing.tenant_id,
        room_label="kitchen",
        weight=1.1,
        labeled_listing_count=5,
    )
    db_session.add(existing)
    await db_session.flush()

    await _add_override_event(db_session, listing, "package.override.rejected", "kitchen")

    agent = LearningAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    await db_session.refresh(existing)
    # rejection should decrease weight
    assert existing.weight < 1.1


@pytest.mark.asyncio
async def test_learning_increments_labeled_listing_count(db_session, listing, assets):
    await _add_override_event(db_session, listing, "package.override.approved", "bedroom")

    agent = LearningAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    weights = (await db_session.execute(select(LearningWeight))).scalars().all()
    assert weights[0].labeled_listing_count == 1
