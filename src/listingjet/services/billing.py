import stripe

from listingjet.config import settings

# Price ID → plan name mapping
PRICE_TO_PLAN: dict[str, str] = {}

# Plan → price ID (reverse)
PLAN_TO_PRICE: dict[str, str] = {}


def _init_price_map():
    """Build price-to-plan map from config. Called lazily so settings are loaded."""
    if not PRICE_TO_PLAN:
        # Primary plan names (stripe_price_starter, stripe_price_pro, stripe_price_enterprise)
        if settings.stripe_price_starter:
            PRICE_TO_PLAN[settings.stripe_price_starter] = "starter"
            PLAN_TO_PRICE["starter"] = settings.stripe_price_starter
        if settings.stripe_price_pro:
            PRICE_TO_PLAN[settings.stripe_price_pro] = "pro"
            PLAN_TO_PRICE["pro"] = settings.stripe_price_pro
        if settings.stripe_price_enterprise:
            PRICE_TO_PLAN[settings.stripe_price_enterprise] = "enterprise"
            PLAN_TO_PRICE["enterprise"] = settings.stripe_price_enterprise

        # Tier-based names (stripe_price_lite, stripe_price_active_agent, stripe_price_team)
        if settings.stripe_price_lite:
            PRICE_TO_PLAN[settings.stripe_price_lite] = "starter"
            PLAN_TO_PRICE.setdefault("starter", settings.stripe_price_lite)
        if settings.stripe_price_active_agent:
            PRICE_TO_PLAN[settings.stripe_price_active_agent] = "pro"
            PLAN_TO_PRICE.setdefault("pro", settings.stripe_price_active_agent)
        if settings.stripe_price_team:
            PRICE_TO_PLAN[settings.stripe_price_team] = "enterprise"
            PLAN_TO_PRICE.setdefault("enterprise", settings.stripe_price_team)


class BillingService:
    def __init__(self):
        self._api_key = settings.stripe_secret_key

    def create_customer(self, email: str, name: str, tenant_id: str) -> str:
        customer = stripe.Customer.create(
            api_key=self._api_key,
            email=email,
            name=name,
            metadata={"tenant_id": tenant_id},
        )
        return customer.id

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        tenant_id: str | None = None,
    ) -> str:
        session = stripe.checkout.Session.create(
            api_key=self._api_key,
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id} if tenant_id else {},
        )
        return session.url

    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        session = stripe.billing_portal.Session.create(
            api_key=self._api_key,
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> stripe.Event:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )

    def resolve_plan(self, price_id: str) -> str:
        _init_price_map()
        plan = PRICE_TO_PLAN.get(price_id)
        if plan is None:
            import logging
            logging.getLogger(__name__).warning(
                "Unknown Stripe price_id=%s — defaulting to starter. "
                "Add the price to settings if this is a new product tier.",
                price_id,
            )
            return "starter"
        return plan

    def get_price_for_plan(self, plan: str) -> str | None:
        _init_price_map()
        return PLAN_TO_PRICE.get(plan)

    def list_invoices(self, customer_id: str, limit: int = 10) -> list[dict]:
        """List recent invoices for a customer."""
        invoices = stripe.Invoice.list(api_key=self._api_key, customer=customer_id, limit=limit)
        return [
            {
                "id": inv.id,
                "number": inv.number,
                "status": inv.status,
                "amount_due": inv.amount_due,
                "amount_paid": inv.amount_paid,
                "currency": inv.currency,
                "period_start": inv.period_start,
                "period_end": inv.period_end,
                "hosted_invoice_url": inv.hosted_invoice_url,
                "pdf": inv.invoice_pdf,
                "created": inv.created,
            }
            for inv in invoices.data
        ]

    def change_subscription_plan(self, subscription_id: str, new_plan: str) -> dict:
        """Upgrade or downgrade a subscription to a new plan."""
        new_price_id = self.get_price_for_plan(new_plan)
        if not new_price_id:
            raise ValueError(f"No price configured for plan: {new_plan}")

        subscription = stripe.Subscription.retrieve(subscription_id, api_key=self._api_key)
        if not subscription.get("items", {}).get("data"):
            raise ValueError("Subscription has no items")

        item_id = subscription["items"]["data"][0].id

        updated = stripe.Subscription.modify(
            subscription_id,
            api_key=self._api_key,
            items=[{"id": item_id, "price": new_price_id}],
            proration_behavior="create_prorations",
        )
        return {
            "subscription_id": updated.id,
            "new_price_id": new_price_id,
            "new_plan": new_plan,
            "status": updated.status,
        }

    def create_usage_record(self, subscription_id: str, quantity: int) -> dict:
        """Report metered usage (per-listing overage). Requires metered price."""
        subscription = stripe.Subscription.retrieve(subscription_id, api_key=self._api_key)
        items = subscription.get("items", {}).get("data", [])
        # Find the metered item (if configured)
        metered_item = None
        for item in items:
            if item.get("price", {}).get("recurring", {}).get("usage_type") == "metered":
                metered_item = item
                break

        if not metered_item:
            return {"reported": False, "reason": "No metered price item on subscription"}

        record = stripe.SubscriptionItem.create_usage_record(
            metered_item.id,
            quantity=quantity,
            action="increment",
        )
        return {"reported": True, "quantity": quantity, "record_id": record.id}
