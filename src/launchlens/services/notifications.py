"""Notification dispatch — sends emails based on user preferences."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.models.listing import Listing
from launchlens.models.notification_preference import NotificationPreference
from launchlens.models.user import User
from launchlens.services.email import get_email_service

logger = logging.getLogger(__name__)


def _listing_address_str(listing: Listing) -> str:
    """Extract a display string from the JSONB address field."""
    addr = listing.address or {}
    if isinstance(addr, str):
        return addr
    return addr.get("street", addr.get("full", str(addr)))


async def _get_tenant_users(session: AsyncSession, tenant_id: str) -> list[User]:
    """Get all users in a tenant (for notification dispatch)."""
    result = await session.execute(
        select(User).where(User.tenant_id == uuid.UUID(tenant_id))
    )
    return list(result.scalars().all())


async def _get_preference(session: AsyncSession, user_id: uuid.UUID) -> NotificationPreference | None:
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def notify_pipeline_complete(session: AsyncSession, listing: Listing, tenant_id: str) -> None:
    """Send pipeline-complete email to tenant users who opted in."""
    email_svc = get_email_service()
    address = _listing_address_str(listing)
    users = await _get_tenant_users(session, tenant_id)

    for user in users:
        pref = await _get_preference(session, user.id)
        if pref and not pref.email_on_complete:
            continue
        try:
            email_svc.send_pipeline_complete(user.email, address, str(listing.id))
        except Exception:
            logger.exception("notify_pipeline_complete_failed", extra={"user_id": str(user.id)})


async def notify_pipeline_failed(session: AsyncSession, listing: Listing, tenant_id: str, error: str) -> None:
    """Send pipeline-failure email to tenant users who opted in."""
    email_svc = get_email_service()
    address = _listing_address_str(listing)
    users = await _get_tenant_users(session, tenant_id)

    for user in users:
        pref = await _get_preference(session, user.id)
        if pref and not pref.email_on_failure:
            continue
        try:
            email_svc.send_pipeline_failed(user.email, address, error)
        except Exception:
            logger.exception("notify_pipeline_failed_failed", extra={"user_id": str(user.id)})


async def notify_review_ready(session: AsyncSession, listing: Listing, tenant_id: str) -> None:
    """Send review-ready email to tenant users who opted in."""
    email_svc = get_email_service()
    address = _listing_address_str(listing)
    users = await _get_tenant_users(session, tenant_id)

    for user in users:
        pref = await _get_preference(session, user.id)
        if pref and not pref.email_on_review_ready:
            continue
        try:
            email_svc.send_review_ready(user.email, address, str(listing.id))
        except Exception:
            logger.exception("notify_review_ready_failed", extra={"user_id": str(user.id)})
