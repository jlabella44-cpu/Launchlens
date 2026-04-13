import uuid
from datetime import datetime

from pydantic import BaseModel


class CreditBalanceResponse(BaseModel):
    balance: int
    granted_balance: int
    purchased_balance: int
    rollover_balance: int
    rollover_cap: int
    period_start: datetime
    period_end: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "balance": 75,
                    "granted_balance": 50,
                    "purchased_balance": 25,
                    "rollover_balance": 10,
                    "rollover_cap": 50,
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
    bundle_size: int  # 25, 50, 100, or 250
    success_url: str
    cancel_url: str
    idempotency_key: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "bundle_size": 50,
                    "success_url": "https://listingjet.ai/credits?success=1",
                    "cancel_url": "https://listingjet.ai/credits?cancelled=1",
                    "idempotency_key": "buy-50-credits-2026-04-06",
                }
            ]
        }
    }


class CreditPurchaseResponse(BaseModel):
    checkout_url: str


class CreditPricingResponse(BaseModel):
    tier: str
    bundles: list[dict]  # [{size, price_cents, per_credit_cents}, ...]


class ServiceCreditCost(BaseModel):
    slug: str
    name: str
    credits: int


class ServiceCostsResponse(BaseModel):
    tier: str
    per_credit_dollar_value: float
    services: list[ServiceCreditCost]
