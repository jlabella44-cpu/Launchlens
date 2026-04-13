import logging
import uuid
from urllib.parse import urlparse

import stripe as stripe_mod
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.billing import (
    BillingStatusResponse,
    ChangePlanRequest,
    CheckoutRequest,
    CheckoutResponse,
    PortalRequest,
    PortalResponse,
)
from listingjet.config import settings
from listingjet.config.tiers import apply_plan_credits
from listingjet.database import get_db
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.billing import BillingService
from listingjet.services.credits import CreditService
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.events import emit_event

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_redirect_url(url: str) -> None:
    """Reject redirect URLs that don't match a configured CORS origin, the
    canonical production domains, or the preview Vercel pattern."""
    import re
    allowed = {o.strip().rstrip("/") for o in settings.cors_origins.split(",")}
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if origin in allowed:
        return
    # Always allow the canonical production domains so env var drift in
    # cors_origins can never break checkout/portal redirects in prod.
    if re.fullmatch(r"https://(www\.)?listingjet\.(ai|com)", origin):
        return
    # Allow preview deployments on the Vercel pattern used in CORS middleware.
    if re.fullmatch(r"https://listingjet[a-z0-9-]*\.vercel\.app", origin):
        return
    raise HTTPException(status_code=400, detail="Redirect URL not allowed")


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_redirect_url(body.success_url)
    _validate_redirect_url(body.cancel_url)

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

    try:
        url = svc.create_checkout_session(
            customer_id=customer_id,
            price_id=body.price_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            tenant_id=str(tenant.id),
        )
    except stripe_mod.RateLimitError:
        raise HTTPException(status_code=503, detail="Payment service is busy — please retry shortly")
    except stripe_mod.APIConnectionError:
        raise HTTPException(status_code=503, detail="Payment service is temporarily unavailable")
    except stripe_mod.StripeError as e:
        logger.error("stripe_checkout_error type=%s message=%s", type(e).__name__, str(e))
        raise HTTPException(status_code=502, detail="Payment processing error")
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
        has_payment_method=bool(tenant.stripe_customer_id),
        has_subscription=bool(tenant.stripe_subscription_id),
    )


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    body: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_redirect_url(body.return_url)

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    svc = BillingService()

    # Create the Stripe customer on-demand so users who have not yet purchased
    # a subscription can still manage payment methods + see invoices.
    if not tenant.stripe_customer_id:
        try:
            tenant.stripe_customer_id = svc.create_customer(
                email=current_user.email,
                name=tenant.name,
                tenant_id=str(tenant.id),
            )
            await db.commit()
        except stripe_mod.StripeError as e:
            logger.error("stripe_customer_create_error type=%s message=%s", type(e).__name__, str(e))
            raise HTTPException(status_code=502, detail="Billing portal temporarily unavailable")

    try:
        url = svc.create_portal_session(
            customer_id=tenant.stripe_customer_id,
            return_url=body.return_url,
        )
    except stripe_mod.StripeError as e:
        logger.error("stripe_portal_error type=%s message=%s", type(e).__name__, str(e))
        raise HTTPException(status_code=502, detail="Billing portal temporarily unavailable")
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
    valid_plans = ("free", "lite", "active_agent", "team")
    if body.plan not in valid_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Must be one of: {', '.join(valid_plans)}")

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

    previous_plan = tenant.plan
    tenant.plan = body.plan
    await db.commit()

    return {
        "previous_plan": previous_plan,
        "new_plan": body.plan,
        "subscription_id": result["subscription_id"],
        "status": result["status"],
    }


# ---------------------------------------------------------------------------
# Stripe Webhook
# ---------------------------------------------------------------------------

async def _find_tenant_by_customer(db: AsyncSession, customer_id: str) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


@router.post("/webhook", dependencies=[Depends(rate_limit(30, 60))])
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
    event_id = event.id  # Used as reference_id for idempotency
    # Convert Stripe's StripeObject to a plain dict — the handlers below use
    # `.get()` extensively, which StripeObject does not expose.
    raw_object = event["data"]["object"]
    if hasattr(raw_object, "to_dict_recursive"):
        data_object = raw_object.to_dict_recursive()
    elif hasattr(raw_object, "to_dict"):
        data_object = raw_object.to_dict()
    else:
        data_object = dict(raw_object)
    credit_svc = CreditService()

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data_object, event_id, svc, credit_svc)

    elif event_type == "customer.subscription.created":
        await _handle_subscription_created(db, data_object, svc)

    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data_object, svc)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data_object)

    elif event_type == "invoice.paid":
        await _handle_invoice_paid(db, data_object, event_id, credit_svc)

    elif event_type == "invoice.payment_failed":
        customer_id = data_object.get("customer")
        if customer_id:
            logger.warning(
                "payment_failed customer=%s invoice=%s",
                customer_id, data_object.get("id"),
            )
            # Find tenant by Stripe customer ID and emit event
            from listingjet.models.tenant import Tenant
            tenant = (await db.execute(
                select(Tenant).where(Tenant.stripe_customer_id == customer_id)
            )).scalar_one_or_none()
            if tenant:
                await emit_event(
                    session=db,
                    event_type="billing.payment_failed",
                    payload={"customer_id": customer_id, "invoice_id": data_object.get("id")},
                    tenant_id=str(tenant.id),
                )
                await db.commit()

    return {"status": "ok"}


async def _handle_checkout_completed(
    db: AsyncSession,
    data_object: dict,
    event_id: str,
    svc: BillingService,
    credit_svc: CreditService,
) -> None:
    metadata = data_object.get("metadata", {})
    tenant_id_str = metadata.get("tenant_id")

    tenant = None
    if tenant_id_str:
        tenant = await db.get(Tenant, uuid.UUID(tenant_id_str))

    # Fallback: look up by customer_id if tenant_id not in metadata
    if not tenant:
        customer_id = data_object.get("customer")
        if customer_id:
            tenant = await _find_tenant_by_customer(db, customer_id)

    if not tenant:
        logger.warning(
            "checkout.session.completed: no tenant found for metadata=%s customer=%s",
            tenant_id_str, data_object.get("customer"),
        )
        return

    # Credit bundle purchase
    if metadata.get("type") == "credit_bundle":
        bundle_size = int(metadata.get("bundle_size", 0))
        if bundle_size > 0:
            await credit_svc.add_credits(
                db, tenant.id, bundle_size,
                transaction_type="purchase",
                reference_type="stripe_event",
                reference_id=event_id,
                description=f"Credit bundle: {bundle_size} credits",
            )
            await emit_event(
                session=db,
                event_type="credit.bundle_fulfilled",
                payload={"bundle_size": bundle_size, "stripe_event_id": event_id},
                tenant_id=str(tenant.id),
            )
            await db.commit()
        return

    # Regular subscription checkout
    tenant.stripe_subscription_id = data_object.get("subscription")
    if not tenant.stripe_customer_id:
        tenant.stripe_customer_id = data_object.get("customer")

    # Resolve plan from subscription — fetch from Stripe since checkout session
    # doesn't include line item details in the webhook payload
    sub_id = data_object.get("subscription")
    resolved_plan = None
    if sub_id:
        try:
            sub_obj = stripe_mod.Subscription.retrieve(sub_id, api_key=svc._api_key)
            # Convert StripeObject → dict (StripeObject does not expose .get)
            if hasattr(sub_obj, "to_dict_recursive"):
                sub = sub_obj.to_dict_recursive()
            elif hasattr(sub_obj, "to_dict"):
                sub = sub_obj.to_dict()
            else:
                sub = dict(sub_obj)
            items = sub.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id", "")
                resolved_plan = svc.resolve_plan(price_id)
        except Exception:
            logger.exception("Could not fetch subscription %s for plan resolution — leaving plan unchanged", sub_id)

    if resolved_plan:
        apply_plan_credits(tenant, resolved_plan)

    await db.commit()


async def _handle_subscription_created(
    db: AsyncSession,
    data_object: dict,
    svc: BillingService,
) -> None:
    """Deterministic plan-set when a subscription is first created.

    This provides a reliable fallback if checkout.session.completed fails to
    resolve the plan (e.g. Stripe API timeout during checkout).
    """
    customer_id = data_object.get("customer")
    if not customer_id:
        return

    tenant = await _find_tenant_by_customer(db, customer_id)
    if not tenant:
        return

    # Set subscription ID if not already set by checkout handler
    sub_id = data_object.get("id")
    if sub_id and not tenant.stripe_subscription_id:
        tenant.stripe_subscription_id = sub_id

    items = data_object.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        new_plan = svc.resolve_plan(price_id)
        apply_plan_credits(tenant, new_plan)

    await db.commit()


async def _handle_subscription_updated(
    db: AsyncSession,
    data_object: dict,
    svc: BillingService,
) -> None:
    customer_id = data_object.get("customer")
    if not customer_id:
        return

    tenant = await _find_tenant_by_customer(db, customer_id)
    if not tenant:
        return

    items = data_object.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        new_plan = svc.resolve_plan(price_id)
        apply_plan_credits(tenant, new_plan)

    await db.commit()


async def _handle_subscription_deleted(
    db: AsyncSession,
    data_object: dict,
) -> None:
    customer_id = data_object.get("customer")
    if not customer_id:
        return

    tenant = await _find_tenant_by_customer(db, customer_id)
    if not tenant:
        return

    # Downgrade to free — CreditAccount balance is preserved (purchased credits are theirs)
    apply_plan_credits(tenant, "free")
    tenant.stripe_subscription_id = None
    await db.commit()


async def _handle_invoice_paid(
    db: AsyncSession,
    data_object: dict,
    event_id: str,
    credit_svc: CreditService,
) -> None:
    customer_id = data_object.get("customer")
    if not customer_id:
        return

    tenant = await _find_tenant_by_customer(db, customer_id)
    if not tenant:
        return

    logger.info(
        "invoice_paid customer=%s amount=%s",
        customer_id, data_object.get("amount_paid"),
    )

    # Grant included credits on subscription renewal
    if tenant.included_credits > 0:
        await credit_svc.process_period_renewal(
            db, tenant.id, tenant.included_credits,
        )
        await db.commit()
