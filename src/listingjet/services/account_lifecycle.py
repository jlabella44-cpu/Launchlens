"""
Account lifecycle — GDPR/CCPA deletion and data export.

delete_tenant_data: cascade-deletes all rows belonging to a tenant.
export_tenant_data: returns a JSON-serialisable dict of all tenant data.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.addon_purchase import AddonPurchase
from listingjet.models.api_key import APIKey
from listingjet.models.asset import Asset
from listingjet.models.audit_log import AuditLog
from listingjet.models.brand_kit import BrandKit
from listingjet.models.credit_account import CreditAccount
from listingjet.models.credit_transaction import CreditTransaction
from listingjet.models.event import Event
from listingjet.models.listing import Listing
from listingjet.models.notification import Notification
from listingjet.models.outbox import Outbox
from listingjet.models.social_content import SocialContent
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.models.video_asset import VideoAsset
from listingjet.models.vision_result import VisionResult

# Tables deleted in dependency order (children first).
# Models with FK cascades (ListingPermission, ListingAuditLog,
# NotificationPreference) are handled automatically by the DB.
_TENANT_SCOPED_TABLES = [
    VisionResult,
    VideoAsset,
    SocialContent,
    Asset,
    Listing,
    BrandKit,
    CreditTransaction,
    CreditAccount,
    AddonPurchase,
    APIKey,
    AuditLog,
    Event,
    Outbox,
    Notification,
]


async def delete_tenant_data(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Delete all data belonging to a tenant, then remove users and tenant."""
    for model in _TENANT_SCOPED_TABLES:
        await db.execute(delete(model).where(model.tenant_id == tenant_id))

    # Delete users (cascades NotificationPreference, ListingPermission, etc.)
    await db.execute(delete(User).where(User.tenant_id == tenant_id))
    # Delete tenant itself
    await db.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def export_tenant_data(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    """Export all personal data for GDPR data-portability requests."""

    def _dt(v: datetime | None) -> str | None:
        return v.isoformat() if v else None

    # User profile
    user = await db.get(User, user_id)
    user_data = {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "created_at": _dt(user.created_at),
    } if user else {}

    # Tenant
    tenant = await db.get(Tenant, tenant_id)
    tenant_data = {
        "id": str(tenant.id),
        "name": tenant.name,
        "plan": tenant.plan,
        "created_at": _dt(tenant.created_at),
    } if tenant else {}

    # Listings
    listings = (await db.execute(
        select(Listing).where(Listing.tenant_id == tenant_id)
    )).scalars().all()
    listings_data = [
        {
            "id": str(l.id),
            "address": l.address,
            "state": l.state.value if l.state else None,
            "created_at": _dt(l.created_at),
        }
        for l in listings
    ]

    # Credit transactions
    txns = (await db.execute(
        select(CreditTransaction).where(CreditTransaction.tenant_id == tenant_id)
    )).scalars().all()
    txns_data = [
        {
            "id": str(t.id),
            "amount": t.amount,
            "transaction_type": t.transaction_type,
            "description": t.description,
            "created_at": _dt(t.created_at),
        }
        for t in txns
    ]

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": user_data,
        "tenant": tenant_data,
        "listings": listings_data,
        "credit_transactions": txns_data,
    }
