"""
Team API — manage team members within a tenant.

Endpoints:
  GET    /team/members              — list users in current tenant (admin+)
  POST   /team/members              — invite new member (admin+)
  PATCH  /team/members/{member_id}/role — change role (admin+)
  DELETE /team/members/{member_id}  — remove member (admin+)
  GET    /team/me                   — current user profile + role
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.team import (
    InviteTeamMemberRequest,
    TeamMemberResponse,
    UpdateRoleRequest,
)
from listingjet.database import get_db
from listingjet.models.user import User, UserRole
from listingjet.services.auth import hash_password

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
    return result.scalars().all()


@router.post("/members", response_model=TeamMemberResponse, status_code=201)
async def invite_member(
    body: InviteTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite (create) a new team member in the current tenant. Requires admin+."""
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

    user = User(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        email=email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=requested_role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


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
