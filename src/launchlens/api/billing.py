from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from launchlens.database import get_db
from launchlens.models.tenant import Tenant
from launchlens.models.user import User
from launchlens.api.deps import get_current_user
from launchlens.services.billing import BillingService
from launchlens.api.schemas.billing import (
    CheckoutRequest, CheckoutResponse,
    PortalRequest, PortalResponse,
    BillingStatusResponse,
)

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    svc = BillingService()

    customer_id = tenant.stripe_customer_id
    if not customer_id:
        customer_id = svc.create_customer(
            email=current_user.email,
            name=tenant.name,
            tenant_id=str(tenant.id),
        )
        tenant.stripe_customer_id = customer_id
        await db.commit()

    url = svc.create_checkout_session(
        customer_id=customer_id,
        price_id=body.price_id,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return CheckoutResponse(checkout_url=url)


@router.get("/status", response_model=BillingStatusResponse)
async def billing_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return BillingStatusResponse(
        plan=tenant.plan,
        stripe_customer_id=tenant.stripe_customer_id,
        stripe_subscription_id=tenant.stripe_subscription_id,
    )


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    body: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account — complete checkout first")

    svc = BillingService()
    url = svc.create_portal_session(
        customer_id=tenant.stripe_customer_id,
        return_url=body.return_url,
    )
    return PortalResponse(portal_url=url)
