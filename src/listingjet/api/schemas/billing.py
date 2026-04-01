from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "price_id": "price_1OaBcDEfGhIjKlMn",
                    "success_url": "https://app.listingjet.com/billing?success=1",
                    "cancel_url": "https://app.listingjet.com/billing?cancelled=1",
                }
            ]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "plan": "pro",
                    "has_payment_method": True,
                    "has_subscription": True,
                }
            ]
        }
    }


class ChangePlanRequest(BaseModel):
    plan: str  # "starter", "pro", "enterprise"
