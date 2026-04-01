"""Listing permission check dependencies for cross-tenant access control."""

import uuid
from enum import IntEnum

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from listingjet.models.listing import Listing
from listingjet.models.listing_permission import ListingPermission
from listingjet.models.user import User, UserRole

PERMISSION_MAP: dict[str, "PermissionLevel"] = {}


class PermissionLevel(IntEnum):
    NONE = 0
    READ = 1
    WRITE = 2
    PUBLISH = 3
    BILLING = 4


PERMISSION_MAP.update(
    {
        "read": PermissionLevel.READ,
        "write": PermissionLevel.WRITE,
        "publish": PermissionLevel.PUBLISH,
        "billing": PermissionLevel.BILLING,
    }
)


async def get_listing_with_permission(
    listing_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
    required_level: PermissionLevel = PermissionLevel.READ,
) -> Listing:
    """Fetch a listing with permission check.

    Returns the listing if the user has at least the required permission level.

    Permission resolution order:
        1. Listing owner (same tenant) -> BILLING (full access)
        2. Admin in listing's tenant -> READ (write needs explicit grant)
        3. Per-listing permission grant (active, not expired, not revoked)
        4. TODO: Blanket per-agent grant (Phase B - listings are tenant-scoped,
           not user-owned, so blanket grants need a per-tenant model)
        5. None -> raise 403/404
    """
    # Load listing without tenant filter (cross-tenant access possible)
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    effective_level = PermissionLevel.NONE

    # 1. Same-tenant user -> owner-level access (BILLING)
    if listing.tenant_id == current_user.tenant_id:
        effective_level = PermissionLevel.BILLING

    # 2. Admin in listing's tenant -> baseline READ
    elif current_user.role in (UserRole.ADMIN, UserRole.SUPERADMIN) and listing.tenant_id == current_user.tenant_id:
        # Note: this branch is unreachable since case 1 already covers same-tenant,
        # but kept for clarity if ownership semantics change later.
        effective_level = max(effective_level, PermissionLevel.READ)

    # 3. Per-listing permission grant
    if effective_level < required_level:
        stmt = (
            select(ListingPermission.permission)
            .where(
                ListingPermission.listing_id == listing_id,
                ListingPermission.grantee_user_id == current_user.id,
                ListingPermission.revoked_at.is_(None),
            )
            .where(
                (ListingPermission.expires_at.is_(None)) | (ListingPermission.expires_at > func.now())
            )
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        for perm_str in rows:
            grant_level = PERMISSION_MAP.get(perm_str, PermissionLevel.NONE)
            effective_level = max(effective_level, grant_level)

    # TODO: Phase B - blanket per-agent grants (listing_permissions with
    # listing_id IS NULL and agent_user_id set). Requires defining how
    # tenant-scoped listings map to agent users.

    if effective_level < required_level:
        # Return 404 for cross-tenant users to avoid leaking listing existence
        if listing.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Listing not found")
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return listing


async def require_listing_read(
    listing_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Listing:
    """Require at least READ permission on a listing."""
    return await get_listing_with_permission(listing_id, current_user, db, PermissionLevel.READ)


async def require_listing_write(
    listing_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Listing:
    """Require at least WRITE permission on a listing."""
    return await get_listing_with_permission(listing_id, current_user, db, PermissionLevel.WRITE)
