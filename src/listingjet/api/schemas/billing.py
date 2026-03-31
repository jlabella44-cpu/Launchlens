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
    has_payment_method: bool = False
    has_subscription: bool = False


class ChangePlanRequest(BaseModel):
    plan: str  # "starter", "pro", "enterprise"
