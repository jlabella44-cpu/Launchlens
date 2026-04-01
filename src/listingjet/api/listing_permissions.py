import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.listing_permission import (
    ListingPermissionResponse,
    ShareListingRequest,
    UpdatePermissionRequest,
)
from listingjet.database import get_db
from listingjet.models.listing import Listing
from listingjet.models.listing_permission import ListingAuditLog, ListingPermission
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_PERMISSIONS = {"read", "write", "publish", "billing"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_listing(db: AsyncSession, listing_id: uuid.UUID) -> Listing:
    listing = await db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


async def _assert_owner_or_admin(listing: Listing, user: User, db: AsyncSession) -> None:
    """Verify the current user is the listing owner (same tenant) or an admin in the listing's tenant."""
    if user.tenant_id == listing.tenant_id:
        if user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
            return
        # Regular user in same tenant — considered owner
        return
    # Cross-tenant: only superadmins
    if user.role == UserRole.SUPERADMIN:
        return
    raise HTTPException(status_code=403, detail="Not authorised to manage this listing")


def _build_permission_response(
    perm: ListingPermission, grantee: User
) -> ListingPermissionResponse:
    return ListingPermissionResponse(
        id=perm.id,
        listing_id=perm.listing_id,
        grantee_user_id=perm.grantee_user_id,
        grantee_email=grantee.email,
        grantee_name=grantee.name,
        permission=perm.permission,
        expires_at=perm.expires_at,
        created_at=perm.created_at,
    )


async def _audit(
    db: AsyncSession,
    listing_id: uuid.UUID,
    user: User,
    action: str,
    details: dict | None = None,
) -> None:
    entry = ListingAuditLog(
        listing_id=listing_id,
        user_id=user.id,
        user_email=user.email,
        user_name=user.name,
        action=action,
        details=details or {},
    )
    db.add(entry)


# ---------------------------------------------------------------------------
# POST /{listing_id}/permissions — Share a listing
# ---------------------------------------------------------------------------

@router.post(
    "/{listing_id}/permissions",
    response_model=ListingPermissionResponse,
    status_code=201,
)
async def share_listing(
    listing_id: uuid.UUID,
    body: ShareListingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = await _load_listing(db, listing_id)
    await _assert_owner_or_admin(listing, user, db)

    # Look up grantee by email (any tenant — enables cross-tenant sharing)
    result = await db.execute(select(User).where(User.email == body.email))
    grantee = result.scalar_one_or_none()
    if not grantee:
        raise HTTPException(status_code=404, detail="User not found with that email")

    # Validate permission level
    if body.permission not in VALID_PERMISSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid permission. Must be one of: {', '.join(sorted(VALID_PERMISSIONS))}",
        )

    # Plan gating
    grantor_tenant = await db.get(Tenant, user.tenant_id)
    if not grantor_tenant:
        raise HTTPException(status_code=404, detail="Grantor tenant not found")

    cross_tenant = grantee.tenant_id != listing.tenant_id
    if cross_tenant:
        # Both tenants must be enterprise
        grantee_tenant = await db.get(Tenant, grantee.tenant_id)
        if grantor_tenant.plan != "enterprise":
            raise HTTPException(
                status_code=403,
                detail="Cross-tenant sharing requires an enterprise plan",
            )
        if not grantee_tenant or grantee_tenant.plan != "enterprise":
            raise HTTPException(
                status_code=403,
                detail="Cross-tenant sharing requires both tenants on an enterprise plan",
            )
    else:
        # Same-tenant: pro or enterprise
        if grantor_tenant.plan not in ("pro", "enterprise"):
            raise HTTPException(
                status_code=403,
                detail="Listing sharing requires a pro or enterprise plan",
            )

    # Create permission
    perm = ListingPermission(
        listing_id=listing.id,
        grantee_user_id=grantee.id,
        grantee_tenant_id=grantee.tenant_id,
        grantor_user_id=user.id,
        grantor_tenant_id=user.tenant_id,
        permission=body.permission,
        expires_at=body.expires_at,
    )
    db.add(perm)

    # Audit log
    await _audit(db, listing.id, user, "share", {
        "grantee_email": grantee.email,
        "permission": body.permission,
    })

    await db.commit()
    await db.refresh(perm)

    return _build_permission_response(perm, grantee)


# ---------------------------------------------------------------------------
# GET /{listing_id}/permissions — List who has access
# ---------------------------------------------------------------------------

@router.get(
    "/{listing_id}/permissions",
    response_model=list[ListingPermissionResponse],
)
async def list_permissions(
    listing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = await _load_listing(db, listing_id)
    await _assert_owner_or_admin(listing, user, db)

    # Active permissions with grantee info
    stmt = (
        select(ListingPermission, User)
        .join(User, User.id == ListingPermission.grantee_user_id)
        .where(
            ListingPermission.listing_id == listing_id,
            ListingPermission.revoked_at.is_(None),
        )
    )
    rows = await db.execute(stmt)
    return [
        _build_permission_response(perm, grantee)
        for perm, grantee in rows.all()
    ]


# ---------------------------------------------------------------------------
# PATCH /{listing_id}/permissions/{permission_id} — Update permission
# ---------------------------------------------------------------------------

@router.patch(
    "/{listing_id}/permissions/{permission_id}",
    response_model=ListingPermissionResponse,
)
async def update_permission(
    listing_id: uuid.UUID,
    permission_id: uuid.UUID,
    body: UpdatePermissionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = await _load_listing(db, listing_id)
    await _assert_owner_or_admin(listing, user, db)

    perm = await db.get(ListingPermission, permission_id)
    if not perm or perm.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="Permission not found")

    if body.permission is not None:
        if body.permission not in VALID_PERMISSIONS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid permission. Must be one of: {', '.join(sorted(VALID_PERMISSIONS))}",
            )
        perm.permission = body.permission

    if body.expires_at is not None:
        perm.expires_at = body.expires_at

    await _audit(db, listing.id, user, "update_permission", {
        "permission_id": str(permission_id),
        "permission": body.permission,
        "expires_at": body.expires_at.isoformat() if body.expires_at else None,
    })

    await db.commit()
    await db.refresh(perm)

    grantee = await db.get(User, perm.grantee_user_id)
    return _build_permission_response(perm, grantee)


# ---------------------------------------------------------------------------
# DELETE /{listing_id}/permissions/{permission_id} — Revoke access
# ---------------------------------------------------------------------------

@router.delete(
    "/{listing_id}/permissions/{permission_id}",
    status_code=204,
)
async def revoke_permission(
    listing_id: uuid.UUID,
    permission_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = await _load_listing(db, listing_id)
    await _assert_owner_or_admin(listing, user, db)

    perm = await db.get(ListingPermission, permission_id)
    if not perm or perm.listing_id != listing_id:
        raise HTTPException(status_code=404, detail="Permission not found")

    # Soft-delete
    perm.revoked_at = datetime.now(timezone.utc)

    await _audit(db, listing.id, user, "unshare", {
        "permission_id": str(permission_id),
        "grantee_user_id": str(perm.grantee_user_id),
    })

    await db.commit()


# ---------------------------------------------------------------------------
# GET /shared-with-me — Listings shared with current user
# ---------------------------------------------------------------------------

@router.get("/shared-with-me")
async def shared_with_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    stmt = (
        select(Listing, ListingPermission)
        .join(Listing, Listing.id == ListingPermission.listing_id)
        .where(
            ListingPermission.grantee_user_id == user.id,
            ListingPermission.revoked_at.is_(None),
            (ListingPermission.expires_at.is_(None)) | (ListingPermission.expires_at > now),
        )
    )
    rows = await db.execute(stmt)
    results = []
    for listing, perm in rows.all():
        results.append({
            "listing_id": listing.id,
            "tenant_id": listing.tenant_id,
            "address": listing.address,
            "state": listing.state.value if hasattr(listing.state, "value") else listing.state,
            "permission": perm.permission,
            "shared_at": perm.created_at,
            "expires_at": perm.expires_at,
        })
    return results
