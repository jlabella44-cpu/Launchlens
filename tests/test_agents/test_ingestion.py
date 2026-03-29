import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.ingestion import IngestionAgent
from listingjet.models.asset import Asset
from listingjet.models.listing import ListingState
from tests.test_agents.conftest import make_session_factory


@pytest.mark.asyncio
async def test_ingestion_transitions_listing_to_analyzing(db_session, listing, assets):
    agent = IngestionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    await db_session.refresh(listing)
    assert listing.state == ListingState.ANALYZING


@pytest.mark.asyncio
async def test_ingestion_marks_assets_as_ingested(db_session, listing, assets):
    agent = IngestionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    await agent.execute(ctx)

    rows = (await db_session.execute(select(Asset).where(Asset.listing_id == listing.id))).scalars().all()
    assert all(a.state == "ingested" for a in rows)


@pytest.mark.asyncio
async def test_ingestion_deduplicates_by_file_hash(db_session, listing, assets):
    # Set two assets to same hash (duplicate)
    assets[1].file_hash = assets[0].file_hash
    await db_session.flush()

    agent = IngestionAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    # Only 2 unique hashes → 2 ingested, 1 duplicate
    ingested = (await db_session.execute(
        select(Asset).where(Asset.listing_id == listing.id, Asset.state == "ingested")
    )).scalars().all()
    assert len(ingested) == 2
    assert result["duplicate_count"] == 1
