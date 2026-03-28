import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_db_admin, require_admin
from launchlens.api.schemas.admin import (
    InviteUserRequest,
    PlatformStatsResponse,
    TenantDetailResponse,
    TenantResponse,
    UpdateTenantRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from launchlens.models.listing import Listing
from launchlens.models.tenant import Tenant
from launchlens.models.user import User, UserRole
from launchlens.services.auth import hash_password

router = APIRouter()


@router.get("/health-detail")
async def health_detail(admin_user: User = Depends(require_admin)):
    return {"status": "ok", "detail": "admin"}


@router.get("/health")
async def admin_health(admin_user: User = Depends(require_admin)):
    return {"status": "ok", "role": admin_user.role.value}


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return result.scalars().all()


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user_count = (await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )).scalar() or 0

    listing_count = (await db.execute(
        select(func.count(Listing.id)).where(Listing.tenant_id == tenant_id)
    )).scalar() or 0

    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        stripe_customer_id=tenant.stripe_customer_id,
        stripe_subscription_id=tenant.stripe_subscription_id,
        webhook_url=tenant.webhook_url,
        created_at=tenant.created_at,
        user_count=user_count,
        listing_count=listing_count,
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: UpdateTenantRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.name is not None:
        tenant.name = body.name
    if body.plan is not None:
        if body.plan not in ("starter", "pro", "enterprise"):
            raise HTTPException(status_code=400, detail="Invalid plan. Must be: starter, pro, enterprise")
        tenant.plan = body.plan
    if body.webhook_url is not None:
        tenant.webhook_url = body.webhook_url or None  # empty string → None

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.post("/tenants/{tenant_id}/test-webhook")
async def test_webhook(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    """Send a test event to the tenant's webhook URL."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not tenant.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook URL configured for this tenant")

    from launchlens.services.webhook_delivery import deliver_webhook

    success = await deliver_webhook(
        url=tenant.webhook_url,
        event_type="webhook.test",
        payload={"message": "This is a test webhook from LaunchLens", "tenant_name": tenant.name},
        tenant_id=str(tenant_id),
    )

    return {
        "delivered": success,
        "webhook_url": tenant.webhook_url,
        "event_type": "webhook.test",
    }


VALID_ROLES = {r.value for r in UserRole}


@router.get("/tenants/{tenant_id}/users", response_model=list[UserResponse])
async def list_users(
    tenant_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
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
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
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
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    body: UpdateUserRoleRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(body.role)
    await db.commit()
    await db.refresh(user)
    return UserResponse.from_orm_user(user)


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_admin),
):
    total_tenants = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_listings = (await db.execute(select(func.count(Listing.id)))).scalar() or 0

    state_rows = (await db.execute(
        select(Listing.state, func.count(Listing.id)).group_by(Listing.state)
    )).all()
    listings_by_state = {
        row[0].value if hasattr(row[0], 'value') else row[0]: row[1]
        for row in state_rows
    }

    return PlatformStatsResponse(
        total_tenants=total_tenants,
        total_users=total_users,
        total_listings=total_listings,
        listings_by_state=listings_by_state,
    )
