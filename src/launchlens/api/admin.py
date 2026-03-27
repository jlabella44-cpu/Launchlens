import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from launchlens.api.deps import require_admin, get_db_admin
from launchlens.models.user import User
from launchlens.models.tenant import Tenant
from launchlens.models.listing import Listing
from launchlens.api.schemas.admin import (
    TenantResponse, TenantDetailResponse, UpdateTenantRequest,
)

router = APIRouter()


@router.get("/health-detail")
async def health_detail():
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

    await db.commit()
    await db.refresh(tenant)
    return tenant
