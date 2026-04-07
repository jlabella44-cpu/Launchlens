"""Tests for account_lifecycle service (GDPR deletion + data export)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.account_lifecycle import delete_tenant_data, export_tenant_data


@pytest.fixture
async def tenant_with_data(db_session: AsyncSession):
    """Create a tenant with a user and listing for deletion tests."""
    tenant = Tenant(name="DeleteMe Corp", plan="free")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="delete@example.com",
        password_hash="hashed",
        name="To Delete",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()

    listing = Listing(
        tenant_id=tenant.id,
        address={"street": "999 Gone St", "city": "Austin", "state": "TX"},
        metadata_={"beds": 3},
        state=ListingState.DRAFT,
    )
    db_session.add(listing)
    await db_session.flush()

    return tenant, user, listing


@pytest.mark.asyncio
async def test_delete_tenant_data_removes_all(db_session: AsyncSession, tenant_with_data):
    tenant, user, listing = tenant_with_data

    await delete_tenant_data(db_session, tenant.id)
    await db_session.flush()

    # Tenant should be gone
    assert await db_session.get(Tenant, tenant.id) is None
    # User should be gone
    assert await db_session.get(User, user.id) is None
    # Listing should be gone
    assert await db_session.get(Listing, listing.id) is None


@pytest.mark.asyncio
async def test_export_tenant_data_returns_user_and_listings(db_session: AsyncSession, tenant_with_data):
    tenant, user, listing = tenant_with_data

    data = await export_tenant_data(db_session, tenant.id, user.id)

    assert data["user"]["email"] == "delete@example.com"
    assert data["tenant"]["name"] == "DeleteMe Corp"
    assert len(data["listings"]) == 1
    assert data["listings"][0]["address"]["street"] == "999 Gone St"
    assert "exported_at" in data
