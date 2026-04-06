"""Credit system API — balance, transactions, purchases, service costs."""
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
    ServiceCostsResponse,
    ServiceCreditCost,
)
from listingjet.config.tiers import (
    CREDIT_BUNDLES,
    SERVICE_CREDIT_COSTS,
    TIER_CREDIT_VALUES,
    TIER_DEFAULTS,
    get_bundles_for_tier,
)
from listingjet.database import get_db
from listingjet.models.user import User
from listingjet.services.billing import BillingService
from listingjet.services.credits import CreditService

logger = logging.getLogger(__name__)

router = APIRouter()

# Bundle size -> Stripe setting name prefix (tier is appended dynamically)
VALID_BUNDLE_SIZES = {25, 50, 100, 250}

# Human-readable names for service slugs
SERVICE_NAMES: dict[str, str] = {
    "base_listing": "Base Listing",
    "ai_video_tour": "AI Video Tour",
    "virtual_staging": "Virtual Staging",
    "3d_floorplan": "3D Floorplan",
    "image_editing": "AI Image Editing",
    "cma_report": "CMA Report",
    "photo_compliance": "Photo Compliance",
    "social_media_cuts": "Social Media Cuts",
    "microsite": "Microsite",
    "social_content_pack": "Social Content Pack",
}


def _get_tenant_tier(user: User) -> str:
    """Resolve the user's tier from their tenant's plan."""
    # The plan field now stores the tier name directly (free/lite/active_agent/team)
    plan = getattr(user, "plan", None) or "free"
    if plan in TIER_DEFAULTS:
        return plan
    # Legacy fallback
    from listingjet.config.tiers import LEGACY_PLAN_MAP
    return LEGACY_PLAN_MAP.get(plan, "free")


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CreditService()
    try:
        balance = await svc.get_balance(db, current_user.tenant_id)
    except ValueError:
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
async def get_credit_pricing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return tier-aware credit bundle pricing."""
    from listingjet.models.tenant import Tenant
    tenant = await db.get(Tenant, current_user.tenant_id)
    tier = tenant.plan if tenant and tenant.plan in CREDIT_BUNDLES else "free"
    return CreditPricingResponse(tier=tier, bundles=get_bundles_for_tier(tier))


@router.get("/service-costs", response_model=ServiceCostsResponse)
async def get_service_costs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the credit cost of each service and the user's per-credit dollar value."""
    from listingjet.models.tenant import Tenant
    tenant = await db.get(Tenant, current_user.tenant_id)
    tier = tenant.plan if tenant and tenant.plan in TIER_DEFAULTS else "free"

    services = [
        ServiceCreditCost(slug=slug, name=SERVICE_NAMES.get(slug, slug), credits=cost)
        for slug, cost in SERVICE_CREDIT_COSTS.items()
    ]

    return ServiceCostsResponse(
        tier=tier,
        per_credit_dollar_value=TIER_CREDIT_VALUES.get(tier, 0.50),
        services=services,
    )


@router.post("/purchase", response_model=CreditPurchaseResponse)
async def purchase_credits(
    body: CreditPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.bundle_size not in VALID_BUNDLE_SIZES:
        raise HTTPException(400, f"Invalid bundle size. Choose from: {sorted(VALID_BUNDLE_SIZES)}")

    from listingjet.config import settings
    from listingjet.models.tenant import Tenant

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    # Resolve tier-specific Stripe price ID
    tier = tenant.plan if tenant.plan in TIER_DEFAULTS else "free"
    setting_name = f"stripe_price_credit_bundle_{tier}_{body.bundle_size}"
    price_id = getattr(settings, setting_name, "")

    # Fallback to legacy bundle settings
    if not price_id:
        legacy_setting = f"stripe_price_credit_bundle_{body.bundle_size}"
        price_id = getattr(settings, legacy_setting, "")

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
    try:
        if body.idempotency_key:
            session = stripe.checkout.Session.create(
                **create_kwargs,
                idempotency_key=body.idempotency_key,
            )
        else:
            session = stripe.checkout.Session.create(**create_kwargs)
    except stripe.CardError:
        raise HTTPException(status_code=402, detail="Payment method was declined")
    except stripe.RateLimitError:
        raise HTTPException(status_code=503, detail="Payment service is busy — please retry shortly")
    except stripe.APIConnectionError:
        raise HTTPException(status_code=503, detail="Payment service is temporarily unavailable")
    except stripe.StripeError as e:
        logger.error("stripe_checkout_error type=%s message=%s", type(e).__name__, str(e))
        raise HTTPException(status_code=502, detail="Payment processing error")
    return CreditPurchaseResponse(checkout_url=session.url)
