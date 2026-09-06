import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.property_verification import PropertyVerificationAgent
from listingjet.models.property_data import PropertyData
from tests.test_agents.conftest import make_session_factory


@pytest.mark.asyncio
async def test_verification_agent_uses_api_data_only(db_session, listing):
    """Agent verifies from API-sourced PropertyData fields only (no scrapers)."""
    property_data = PropertyData(
        listing_id=listing.id,
        address_hash="abc123",
        property_status="normal",
        beds=3,
        baths=2,
        sqft=1800,
    )
    db_session.add(property_data)
    await db_session.flush()

    agent = PropertyVerificationAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["verification_status"] == "api_only"
    assert result["mismatches"] == []
    assert result["sources_checked"] == ["attom"]

    await db_session.refresh(property_data)
    assert property_data.verification_status == "api_only"
    assert property_data.verified_at is not None
    assert property_data.scraped_data == {}
    assert property_data.field_confidence == {
        "beds": 0.5, "baths": 0.5, "sqft": 0.5,
    }


@pytest.mark.asyncio
async def test_verification_skips_never_listed(db_session, listing):
    """Agent returns skipped immediately for never_listed properties."""
    property_data = PropertyData(
        listing_id=listing.id,
        address_hash="abc123",
        property_status="never_listed",
        beds=3,
        baths=2,
    )
    db_session.add(property_data)
    await db_session.flush()

    agent = PropertyVerificationAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result == {"verification_status": "skipped"}


@pytest.mark.asyncio
async def test_verification_unverified_when_no_api_data(db_session, listing):
    """Agent marks unverified when there is no API-sourced data to check."""
    property_data = PropertyData(
        listing_id=listing.id,
        address_hash="abc123",
        property_status="normal",
    )
    db_session.add(property_data)
    await db_session.flush()

    agent = PropertyVerificationAgent(session_factory=make_session_factory(db_session))
    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    assert result["verification_status"] == "unverified"
    assert result["sources_checked"] == []
