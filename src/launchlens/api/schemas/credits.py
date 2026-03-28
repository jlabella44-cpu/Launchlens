import uuid
from datetime import datetime

from pydantic import BaseModel


class CreditBalanceResponse(BaseModel):
    balance: int
    rollover_balance: int
    rollover_cap: int
    period_start: datetime
    period_end: datetime


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


class CreditPurchaseResponse(BaseModel):
    checkout_url: str


class CreditPricingResponse(BaseModel):
    bundles: list[dict]  # [{size: 5, price_cents: 9500, per_credit_cents: 1900}, ...]
