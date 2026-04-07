"""Tests for the notification dispatch service."""
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing, ListingState
from listingjet.models.notification_preference import NotificationPreference
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.notifications import (
    _listing_address_str,
    notify_pipeline_complete,
)


def test_listing_address_str_from_dict():
    listing = MagicMock()
    listing.address = {"street": "123 Main St", "city": "Austin"}
    assert _listing_address_str(listing) == "123 Main St"


def test_listing_address_str_from_string():
    listing = MagicMock()
    listing.address = "456 Oak Ave"
    assert _listing_address_str(listing) == "456 Oak Ave"


def test_listing_address_str_from_none():
    listing = MagicMock()
    listing.address = None
    result = _listing_address_str(listing)
    assert isinstance(result, str)


@pytest.fixture
async def tenant_with_user(db_session: AsyncSession):
    tenant = Tenant(name="NotifyCo", plan="free")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id, email="notify@example.com",
        password_hash="hashed", name="Notifier", role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()

    listing = Listing(
        tenant_id=tenant.id,
        address={"street": "100 Notify Ln"},
        metadata_={},
        state=ListingState.DELIVERED,
    )
    db_session.add(listing)
    await db_session.flush()

    return tenant, user, listing


@pytest.mark.asyncio
async def test_notify_pipeline_complete_sends_email(db_session, tenant_with_user):
    tenant, user, listing = tenant_with_user

    with patch("listingjet.services.notifications.get_email_service") as mock_get:
        mock_svc = MagicMock()
        mock_get.return_value = mock_svc

        await notify_pipeline_complete(db_session, listing, str(tenant.id))

        mock_svc.send_pipeline_complete.assert_called_once_with(
            user.email, "100 Notify Ln", str(listing.id),
        )


@pytest.mark.asyncio
async def test_notify_skips_opted_out_user(db_session, tenant_with_user):
    tenant, user, listing = tenant_with_user

    # Opt out of completion emails
    pref = NotificationPreference(user_id=user.id, email_on_complete=False)
    db_session.add(pref)
    await db_session.flush()

    with patch("listingjet.services.notifications.get_email_service") as mock_get:
        mock_svc = MagicMock()
        mock_get.return_value = mock_svc

        await notify_pipeline_complete(db_session, listing, str(tenant.id))

        mock_svc.send_pipeline_complete.assert_not_called()
