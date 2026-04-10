"""
Team API — manage team members within a tenant.

Endpoints:
  GET    /team/members              — list users in current tenant (admin+)
  POST   /team/members              — invite new member (admin+); sends
                                       an invite email with an accept link
  PATCH  /team/members/{member_id}/role — change role (admin+)
  DELETE /team/members/{member_id}  — remove member (admin+)
  GET    /team/me                   — current user profile + role
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.listing_permission import (
    BlanketGrantRequest,
    BlanketGrantResponse,
)
from listingjet.api.schemas.team import (
    InviteTeamMemberRequest,
    InviteTeamMemberResponse,
    TeamMemberResponse,
    UpdateRoleRequest,
)
from listingjet.config import settings
from listingjet.database import get_db
from listingjet.models.listing_permission import ListingPermission
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.auth import generate_invite_token
from listingjet.services.email import get_email_service

logger = logging.getLogger(__name__)

INVITE_EXPIRY_HOURS = 72

router = APIRouter()


def _require_admin(current_user: User) -> None:
    """Raise 403 if the user is not an admin or superadmin."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(status_code=403, detail="Admin role required")


@router.get("/me", response_model=TeamMemberResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Current user's profile and role within the tenant."""
    return current_user


@router.get("/members", response_model=list[TeamMemberResponse])
async def list_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the current tenant. Requires admin+."""
    _require_admin(current_user)
    result = await db.execute(
        select(User)
        .where(User.tenant_id == current_user.tenant_id)
        .order_by(User.created_at)
    )
    members = result.scalars().all()
    return [_to_team_member_response(u) for u in members]


def _to_team_member_response(user: User) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value,
        created_at=user.created_at,
        pending_invite=user.password_hash is None,
    )


def _build_invite_accept_url(raw_token: str) -> str:
    base = (settings.frontend_url or "https://app.listingjet.com").rstrip("/")
    return f"{base}/accept-invite?token={raw_token}"


@router.post("/members", response_model=InviteTeamMemberResponse, status_code=201)
async def invite_member(
    body: InviteTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new team member. Creates a pending user row, generates a
    signed invite token, and emails the invitee an accept link.

    The admin does NOT set the invitee's password — the invitee sets it
    themselves via POST /auth/accept-invite.
    """
    _require_admin(current_user)

    # Validate requested role
    try:
        requested_role = UserRole(body.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {body.role}. Must be one of: {', '.join(r.value for r in UserRole)}",
        )

    # Admin cannot escalate to superadmin
    if requested_role == UserRole.SUPERADMIN and current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Cannot assign superadmin role")

    # Check for duplicate email
    email = body.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Generate invite token. Raw goes in the email, hash goes in the DB.
    raw_token, token_hash = generate_invite_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITE_EXPIRY_HOURS)

    user = User(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        email=email,
        password_hash=None,  # will be set when the invitee accepts
        name=body.name,
        role=requested_role,
        invite_token_hash=token_hash,
        invite_expires_at=expires_at,
        invited_by_user_id=current_user.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send the invite email. Fire-and-forget — failure to send should not
    # block the invitation record.
    try:
        tenant = await db.get(Tenant, current_user.tenant_id)
        email_svc = get_email_service()
        email_svc.send_notification(
            user.email,
            "team_member_invite",
            inviter_name=current_user.name or current_user.email,
            tenant_name=tenant.name if tenant else "your team",
            accept_url=_build_invite_accept_url(raw_token),
            expires_hours=INVITE_EXPIRY_HOURS,
        )
    except Exception as exc:
        logger.warning(
            "team_invite.email_failed user=%s error=%s", user.id, exc
        )

    return InviteTeamMemberResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        invite_expires_at=expires_at,
    )


@router.patch("/members/{member_id}/role", response_model=TeamMemberResponse)
async def update_member_role(
    member_id: uuid.UUID,
    body: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change a team member's role. Requires admin+."""
    _require_admin(current_user)

    # Validate requested role
    try:
        new_role = UserRole(body.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {body.role}. Must be one of: {', '.join(r.value for r in UserRole)}",
        )

    # Admin cannot escalate to superadmin
    if new_role == UserRole.SUPERADMIN and current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Cannot assign superadmin role")

    # Load member scoped to tenant
    member = await db.get(User, member_id)
    if not member or member.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Member not found")

    member.role = new_role
    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=204)
async def remove_member(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a team member. Requires admin+. Cannot remove yourself."""
    _require_admin(current_user)

    if member_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    member = await db.get(User, member_id)
    if not member or member.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(member)
    await db.commit()


# ---------------------------------------------------------------------------
# Blanket listing access grants (Phase B)
# ---------------------------------------------------------------------------

def _build_blanket_response(perm: ListingPermission, grantee: User) -> BlanketGrantResponse:
    return BlanketGrantResponse(
        id=perm.id,
        agent_user_id=perm.agent_user_id,
        agent_name=None,
        agent_email=None,
        grantee_user_id=perm.grantee_user_id,
        permission=perm.permission,
        created_at=perm.created_at,
    )


@router.post(
    "/members/{user_id}/listing-access",
    response_model=BlanketGrantResponse,
    status_code=201,
)
async def create_blanket_grant(
    user_id: uuid.UUID,
    body: BlanketGrantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant blanket access to all listings within the tenant for a user."""
    _require_admin(current_user)

    if body.permission not in ("read", "write"):
        raise HTTPException(status_code=422, detail="Blanket permission must be 'read' or 'write'")

    # Validate target user exists and is in the same tenant
    target_user = await db.get(User, user_id)
    if not target_user or target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found in your tenant")

    # Check for existing active blanket grant
    existing = await db.execute(
        select(ListingPermission).where(
            ListingPermission.listing_id.is_(None),
            ListingPermission.grantee_user_id == user_id,
            ListingPermission.grantor_tenant_id == current_user.tenant_id,
            ListingPermission.revoked_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already has an active blanket grant")

    perm = ListingPermission(
        listing_id=None,
        agent_user_id=None,
        grantee_user_id=user_id,
        grantee_tenant_id=target_user.tenant_id,
        grantor_user_id=current_user.id,
        grantor_tenant_id=current_user.tenant_id,
        permission=body.permission,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)

    return _build_blanket_response(perm, target_user)


@router.get(
    "/members/{user_id}/listing-access",
    response_model=list[BlanketGrantResponse],
)
async def list_blanket_grants(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List blanket listing access grants for a specific user."""
    _require_admin(current_user)

    target_user = await db.get(User, user_id)
    if not target_user or target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User not found in your tenant")

    stmt = (
        select(ListingPermission)
        .where(
            ListingPermission.listing_id.is_(None),
            ListingPermission.grantee_user_id == user_id,
            ListingPermission.grantor_tenant_id == current_user.tenant_id,
            ListingPermission.revoked_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    return [_build_blanket_response(perm, target_user) for perm in result.scalars().all()]


@router.delete(
    "/members/{user_id}/listing-access/{permission_id}",
    status_code=204,
)
async def revoke_blanket_grant(
    user_id: uuid.UUID,
    permission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a blanket listing access grant (soft-delete)."""
    _require_admin(current_user)

    perm = await db.get(ListingPermission, permission_id)
    if (
        not perm
        or perm.listing_id is not None
        or perm.grantee_user_id != user_id
        or perm.grantor_tenant_id != current_user.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Blanket grant not found")

    if perm.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Grant already revoked")

    perm.revoked_at = datetime.now(timezone.utc)
    await db.commit()
