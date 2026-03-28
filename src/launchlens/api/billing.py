import logging
import uuid

import stripe as stripe_mod
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_current_user
from launchlens.api.schemas.billing import (
    BillingStatusResponse,
    ChangePlanRequest,
    CheckoutRequest,
    CheckoutResponse,
    PortalRequest,
    PortalResponse,
)
from launchlens.database import get_db
from launchlens.models.tenant import Tenant
from launchlens.models.user import User
from launchlens.services.billing import BillingService

logger = logging.getLogger(__name__)

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


@router.get("/invoices")
async def list_invoices(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent invoices from Stripe."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant.stripe_customer_id:
        return {"invoices": []}

    svc = BillingService()
    invoices = svc.list_invoices(tenant.stripe_customer_id, limit=min(limit, 50))
    return {"invoices": invoices}


@router.post("/change-plan")
async def change_plan(
    body: ChangePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upgrade or downgrade subscription plan."""
    if body.plan not in ("starter", "pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid plan. Must be: starter, pro, enterprise")

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.plan == body.plan:
        raise HTTPException(status_code=400, detail=f"Already on {body.plan} plan")

    if not tenant.stripe_subscription_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription. Use /billing/checkout to subscribe first.",
        )

    svc = BillingService()
    try:
        result = svc.change_subscription_plan(tenant.stripe_subscription_id, body.plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tenant.plan = body.plan
    await db.commit()

    return {
        "previous_plan": tenant.plan,
        "new_plan": body.plan,
        "subscription_id": result["subscription_id"],
        "status": result["status"],
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    svc = BillingService()
    try:
        event = svc.construct_webhook_event(payload, sig_header)
    except (stripe_mod.SignatureVerificationError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.type
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        tenant_id_str = data_object.get("metadata", {}).get("tenant_id")
        if tenant_id_str:
            tenant = await db.get(Tenant, uuid.UUID(tenant_id_str))
            if tenant:
                tenant.stripe_subscription_id = data_object.get("subscription")
                if not tenant.stripe_customer_id:
                    tenant.stripe_customer_id = data_object.get("customer")
                # Resolve plan from checkout session line items
                line_items = data_object.get("line_items", {}).get("data", [])
                if line_items:
                    price_id = line_items[0].get("price", {}).get("id", "")
                    tenant.plan = svc.resolve_plan(price_id)
                else:
                    # Fallback: fetch line items from subscription
                    sub_id = data_object.get("subscription")
                    if sub_id:
                        try:
                            sub = stripe_mod.Subscription.retrieve(sub_id)
                            sub_items = sub.get("items", {}).get("data", [])
                            if sub_items:
                                price_id = sub_items[0].get("price", {}).get("id", "")
                                tenant.plan = svc.resolve_plan(price_id)
                        except Exception:
                            logger.warning("Could not fetch subscription %s for plan resolution", sub_id)
                            tenant.plan = "pro"
                    else:
                        tenant.plan = "pro"
                await db.commit()

    elif event_type == "customer.subscription.updated":
        customer_id = data_object.get("customer")
        if customer_id:
            tenant = (await db.execute(
                select(Tenant).where(Tenant.stripe_customer_id == customer_id)
            )).scalar_one_or_none()
            if tenant:
                items = data_object.get("items", {}).get("data", [])
                if items:
                    price_id = items[0].get("price", {}).get("id", "")
                    tenant.plan = svc.resolve_plan(price_id)
                await db.commit()

    elif event_type == "customer.subscription.deleted":
        customer_id = data_object.get("customer")
        if customer_id:
            tenant = (await db.execute(
                select(Tenant).where(Tenant.stripe_customer_id == customer_id)
            )).scalar_one_or_none()
            if tenant:
                tenant.plan = "starter"
                tenant.stripe_subscription_id = None
                await db.commit()

    elif event_type == "invoice.payment_failed":
        customer_id = data_object.get("customer")
        if customer_id:
            logger.warning("payment_failed customer=%s invoice=%s", customer_id, data_object.get("id"))
            # Don't downgrade immediately — Stripe retries. Log for monitoring.

    elif event_type == "invoice.paid":
        customer_id = data_object.get("customer")
        if customer_id:
            logger.info("invoice_paid customer=%s amount=%s", customer_id, data_object.get("amount_paid"))

    return {"status": "ok"}
