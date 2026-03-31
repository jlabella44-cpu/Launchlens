from unittest.mock import AsyncMock, patch

import pytest

from listingjet.agents.base import AgentContext
from listingjet.agents.property_verification import PropertyVerificationAgent
from listingjet.models.property_data import PropertyData
from tests.test_agents.conftest import make_session_factory


@pytest.mark.asyncio
async def test_verification_agent_runs_scrapers_and_stores_result(db_session, listing):
    """Agent calls scrapers, cross-references, and writes verification_status='verified'."""
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

    scraped_result = {
        "zillow": {"beds": 3, "baths": 2, "sqft": 1800},
        "redfin": {"beds": 3, "baths": 2, "sqft": 1800},
    }

    with patch(
        "listingjet.agents.property_verification.run_all_scrapers",
        new=AsyncMock(return_value=scraped_result),
    ):
        agent = PropertyVerificationAgent(session_factory=make_session_factory(db_session))
        ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
        result = await agent.execute(ctx)

    assert result["verification_status"] == "verified"
    assert result["mismatches"] == []
    assert set(result["sources_checked"]) == {"zillow", "redfin"}

    await db_session.refresh(property_data)
    assert property_data.verification_status == "verified"
    assert property_data.verified_at is not None
    assert property_data.scraped_data == scraped_result


@pytest.mark.asyncio
async def test_verification_skips_never_listed(db_session, listing):
    """Agent returns skipped immediately without calling scrapers for never_listed properties."""
    property_data = PropertyData(
        listing_id=listing.id,
        address_hash="abc123",
        property_status="never_listed",
        beds=3,
        baths=2,
    )
    db_session.add(property_data)
    await db_session.flush()

    with patch(
        "listingjet.agents.property_verification.run_all_scrapers",
        new=AsyncMock(return_value={}),
    ) as mock_scrapers:
        agent = PropertyVerificationAgent(session_factory=make_session_factory(db_session))
        ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
        result = await agent.execute(ctx)

    assert result == {"verification_status": "skipped"}
    mock_scrapers.assert_not_called()
