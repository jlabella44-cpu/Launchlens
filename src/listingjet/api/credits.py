"""Credit system API — balance, transactions, purchases."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.credits import (
    CreditBalanceResponse,
    CreditPricingResponse,
    CreditPurchaseRequest,
    CreditPurchaseResponse,
    CreditTransactionResponse,
)
from listingjet.config.tiers import CREDIT_BUNDLES
from listingjet.database import get_db
from listingjet.models.user import User
from listingjet.services.billing import BillingService
from listingjet.services.credits import CreditService

logger = logging.getLogger(__name__)

router = APIRouter()

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

    from listingjet.config import settings
    from listingjet.models.tenant import Tenant

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
    create_kwargs = dict(
        customer=tenant.stripe_customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"tenant_id": str(tenant.id), "bundle_size": str(body.bundle_size), "type": "credit_bundle"},
    )
    if body.idempotency_key:
        session = stripe.checkout.Session.create(
            **create_kwargs,
            idempotency_key=body.idempotency_key,
        )
    else:
        session = stripe.checkout.Session.create(**create_kwargs)
    return CreditPurchaseResponse(checkout_url=session.url)
