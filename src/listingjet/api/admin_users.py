import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_db_admin, require_superadmin
from listingjet.api.schemas.admin import (
    AdminUserResponse,
    InviteUserRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from listingjet.models.tenant import Tenant
from listingjet.models.user import User, UserRole
from listingjet.services.audit import audit_log
from listingjet.services.auth import hash_password

router = APIRouter()

VALID_ROLES = {r.value for r in UserRole}


@router.get("/tenants/{tenant_id}/users", response_model=list[UserResponse])
async def list_users(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all users belonging to a tenant. Requires superadmin."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
    )
    return [UserResponse.from_orm_user(u) for u in result.scalars().all()]


@router.post("/tenants/{tenant_id}/users", status_code=201, response_model=UserResponse)
async def invite_user(
    tenant_id: uuid.UUID,
    body: InviteUserRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Create a new user under the given tenant. Returns 409 if email is already registered. Requires superadmin."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole(body.role),
    )
    db.add(user)
    await audit_log(
        db, admin_user.id, "invite_user", "user", str(user.id),
        tenant_id=tenant_id,
        details={"email": body.email, "role": body.role},
    )
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    body: UpdateUserRoleRequest,
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Change a user's role (e.g. viewer → admin). Requires superadmin."""
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(body.role)
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)


# ── Users (cross-tenant) ─────────────────────────────────────────────


@router.get("/users", response_model=list[AdminUserResponse])
async def admin_list_all_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    tenant_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_admin),
):
    """List all users across tenants with filters."""
    query = select(
        User, Tenant.name.label("tenant_name")
    ).join(Tenant, User.tenant_id == Tenant.id)

    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
        )
    if role:
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        query = query.where(User.role == UserRole(role))
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)

    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).all()

    return [
        AdminUserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            tenant_name=tenant_name,
            email=user.email,
            name=user.name,
            role=user.role.value if hasattr(user.role, "value") else user.role,
            created_at=user.created_at,
        )
        for user, tenant_name in rows
    ]
