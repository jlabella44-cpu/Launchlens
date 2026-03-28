from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalRequest(BaseModel):
    return_url: str


class PortalResponse(BaseModel):
    portal_url: str


class BillingStatusResponse(BaseModel):
    plan: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None


class ChangePlanRequest(BaseModel):
    plan: str  # "starter", "pro", "enterprise"
