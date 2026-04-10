"""Tests for the DRAFT listing creation flow."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from listingjet.models.listing import ListingState
from listingjet.services.listing_creation import ListingCreationService


@pytest.fixture
def mock_session():
    # Use MagicMock as the base so sync methods like session.add() don't
    # return unawaited coroutines. Mark only the real async methods as AsyncMock.
    session = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    return session


@pytest.fixture
def credit_tenant():
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.billing_model = "credit"
    tenant.per_listing_credit_cost = 15
    tenant.plan = "active_agent"
    return tenant


@pytest.mark.asyncio
async def test_create_listing_creates_draft(mock_session, credit_tenant):
    """Credit-billed listings should be created in DRAFT state with no credit deduction."""
    svc = ListingCreationService()
    listing = await svc.create(
        session=mock_session,
        tenant=credit_tenant,
        tenant_id=credit_tenant.id,
        address={"street": "123 Main St", "city": "Austin", "state": "TX"},
        metadata={},
    )
    assert listing.state == ListingState.DRAFT
    assert listing.credit_cost is None


@pytest.mark.asyncio
async def test_create_listing_no_credit_deduction_for_draft(mock_session, credit_tenant):
    """No credits should be deducted when creating a DRAFT listing."""
    mock_credit_svc = AsyncMock()
    svc = ListingCreationService(credit_svc=mock_credit_svc)
    await svc.create(
        session=mock_session,
        tenant=credit_tenant,
        tenant_id=credit_tenant.id,
        address={"street": "123 Main St"},
        metadata={},
    )
    mock_credit_svc.deduct_credits.assert_not_called()
