import pytest
from launchlens.agents.distribution import DistributionAgent
from launchlens.agents.base import AgentContext
from launchlens.models.listing import ListingState
from launchlens.models.outbox import Outbox
from sqlalchemy import select
from tests.test_agents.conftest import make_session_factory


@pytest.mark.asyncio
async def test_distribution_transitions_to_delivered(db_session, listing, assets):
    listing.state = ListingState.APPROVED
    await db_session.flush()

    agent = DistributionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    await db_session.refresh(listing)
    assert listing.state == ListingState.DELIVERED
    assert result["status"] == "delivered"


@pytest.mark.asyncio
async def test_distribution_emits_pipeline_completed(db_session, listing, assets):
    listing.state = ListingState.APPROVED
    await db_session.flush()

    agent = DistributionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)
    await db_session.flush()

    rows = (await db_session.execute(
        select(Outbox).where(Outbox.event_type == "pipeline.completed")
    )).scalars().all()
    assert len(rows) == 1
