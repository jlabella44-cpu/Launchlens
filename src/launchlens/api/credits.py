"""Credit system API — balance, transactions, purchases."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from launchlens.api.deps import get_current_user
from launchlens.api.schemas.credits import (
    CreditBalanceResponse,
    CreditPricingResponse,
    CreditPurchaseRequest,
    CreditPurchaseResponse,
    CreditTransactionResponse,
)
from launchlens.database import get_db
from launchlens.models.user import User
from launchlens.services.billing import BillingService
from launchlens.services.credits import CreditService

logger = logging.getLogger(__name__)

router = APIRouter()

# Per-listing credit cost by tier (cents)
PER_LISTING_PRICE_CENTS = {
    "free": 3400,           # $34/listing
    "lite": 2400,           # $24/listing
    "active_agent": 2400,   # $24/listing
    "team": 1700,           # $17/listing (volume)
}

# Credit bundles — priced at the agent's tier rate
CREDIT_BUNDLES = [
    {"size": 1, "price_cents": 3400, "per_credit_cents": 3400, "label": "Single Listing"},
    {"size": 3, "price_cents": 7200, "per_credit_cents": 2400, "label": "3-Pack"},
    {"size": 5, "price_cents": 10000, "per_credit_cents": 2000, "label": "5-Pack"},
    {"size": 10, "price_cents": 17000, "per_credit_cents": 1700, "label": "10-Pack"},
    {"size": 25, "price_cents": 37500, "per_credit_cents": 1500, "label": "25-Pack"},
]

BUNDLE_SIZE_TO_STRIPE_SETTING = {
    5: "stripe_price_credit_bundle_5",
    10: "stripe_price_credit_bundle_10",
    25: "stripe_price_credit_bundle_25",
    50: "stripe_price_credit_bundle_50",
}


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CreditService()
    try:
        balance = await svc.get_balance(db, current_user.tenant_id)
    except ValueError:
        # No credit account yet — create one
        await svc.ensure_account(db, current_user.tenant_id)
        await db.commit()
        balance = await svc.get_balance(db, current_user.tenant_id)
    return balance


@router.get("/transactions", response_model=list[CreditTransactionResponse])
async def get_credit_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CreditService()
    return await svc.get_transactions(db, current_user.tenant_id, limit=limit, offset=offset)


@router.get("/pricing", response_model=CreditPricingResponse)
async def get_credit_pricing():
    return CreditPricingResponse(bundles=CREDIT_BUNDLES)


@router.post("/purchase", response_model=CreditPurchaseResponse)
async def purchase_credits(
    body: CreditPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.bundle_size not in BUNDLE_SIZE_TO_STRIPE_SETTING:
        raise HTTPException(400, f"Invalid bundle size. Choose from: {list(BUNDLE_SIZE_TO_STRIPE_SETTING.keys())}")

    from launchlens.config import settings
    from launchlens.models.tenant import Tenant

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    setting_name = BUNDLE_SIZE_TO_STRIPE_SETTING[body.bundle_size]
    price_id = getattr(settings, setting_name, "")
    if not price_id:
        raise HTTPException(501, "Credit bundle pricing not configured")

    billing_svc = BillingService()
    if not tenant.stripe_customer_id:
        tenant.stripe_customer_id = billing_svc.create_customer(
            email=current_user.email, name=tenant.name, tenant_id=str(tenant.id),
        )
        await db.commit()

    import stripe
    session = stripe.checkout.Session.create(
        customer=tenant.stripe_customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"tenant_id": str(tenant.id), "bundle_size": str(body.bundle_size), "type": "credit_bundle"},
    )
    return CreditPurchaseResponse(checkout_url=session.url)
