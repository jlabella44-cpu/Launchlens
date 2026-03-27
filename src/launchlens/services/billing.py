import stripe
from launchlens.config import settings

# Price ID → plan name mapping
PRICE_TO_PLAN: dict[str, str] = {}


def _init_price_map():
    """Build price-to-plan map from config. Called lazily so settings are loaded."""
    if not PRICE_TO_PLAN:
        if settings.stripe_price_starter:
            PRICE_TO_PLAN[settings.stripe_price_starter] = "starter"
        if settings.stripe_price_pro:
            PRICE_TO_PLAN[settings.stripe_price_pro] = "pro"
        if settings.stripe_price_enterprise:
            PRICE_TO_PLAN[settings.stripe_price_enterprise] = "enterprise"


class BillingService:
    def __init__(self):
        stripe.api_key = settings.stripe_secret_key

    def create_customer(self, email: str, name: str, tenant_id: str) -> str:
        customer = stripe.Customer.create(
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
    ) -> str:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url

    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        session = stripe.billing_portal.Session.create(
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
        return PRICE_TO_PLAN.get(price_id, "starter")
