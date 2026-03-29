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


async def _dispatch_notification(
    session: AsyncSession,
    listing: Listing,
    tenant_id: str,
    pref_attr: str,
    send_fn_name: str,
    extra_args: tuple = (),
) -> None:
    """Shared dispatch: send an email to opted-in tenant users."""
    email_svc = get_email_service()
    address = _listing_address_str(listing)
    users = await _get_tenant_users(session, tenant_id)

    for user in users:
        pref = await _get_preference(session, user.id)
        if pref and not getattr(pref, pref_attr, True):
            continue
        try:
            getattr(email_svc, send_fn_name)(user.email, address, *extra_args)
        except Exception:
            logger.exception("%s_failed", send_fn_name, extra={"user_id": str(user.id)})


async def notify_pipeline_complete(session: AsyncSession, listing: Listing, tenant_id: str) -> None:
    """Send pipeline-complete email to tenant users who opted in."""
    await _dispatch_notification(
        session, listing, tenant_id,
        pref_attr="email_on_complete",
        send_fn_name="send_pipeline_complete",
        extra_args=(str(listing.id),),
    )


async def notify_pipeline_failed(session: AsyncSession, listing: Listing, tenant_id: str, error: str) -> None:
    """Send pipeline-failure email to tenant users who opted in."""
    await _dispatch_notification(
        session, listing, tenant_id,
        pref_attr="email_on_failure",
        send_fn_name="send_pipeline_failed",
        extra_args=(error,),
    )


async def notify_review_ready(session: AsyncSession, listing: Listing, tenant_id: str) -> None:
    """Send review-ready email to tenant users who opted in."""
    await _dispatch_notification(
        session, listing, tenant_id,
        pref_attr="email_on_review_ready",
        send_fn_name="send_review_ready",
        extra_args=(str(listing.id),),
    )
