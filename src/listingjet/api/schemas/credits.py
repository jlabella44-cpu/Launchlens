import uuid
from datetime import datetime

from pydantic import BaseModel


class CreditBalanceResponse(BaseModel):
    balance: int
    rollover_balance: int
    rollover_cap: int
    period_start: datetime
    period_end: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "balance": 12,
                    "rollover_balance": 2,
                    "rollover_cap": 5,
                    "period_start": "2024-01-01T00:00:00Z",
                    "period_end": "2024-02-01T00:00:00Z",
                }
            ]
        }
    }


class CreditTransactionResponse(BaseModel):
    id: uuid.UUID
    amount: int
    balance_after: int
    transaction_type: str
    reference_type: str | None
    reference_id: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreditPurchaseRequest(BaseModel):
    bundle_size: int  # 5, 10, 25, or 50
    success_url: str
    cancel_url: str
    idempotency_key: str | None = None  # Client-generated key to prevent duplicate purchases

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "bundle_size": 10,
                    "success_url": "https://app.listingjet.com/credits?success=1",
                    "cancel_url": "https://app.listingjet.com/credits?cancelled=1",
                    "idempotency_key": "buy-10-credits-2024-01-15",
                }
            ]
        }
    }


class CreditPurchaseResponse(BaseModel):
    checkout_url: str


class CreditPricingResponse(BaseModel):
    bundles: list[dict]  # [{size: 5, price_cents: 9500, per_credit_cents: 1900}, ...]
