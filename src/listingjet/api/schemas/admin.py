import uuid
from datetime import datetime

from pydantic import BaseModel


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    webhook_url: str | None
    credit_balance: int = 0
    deactivated_at: datetime | None = None
    bypass_limits: bool = False
    plan_overrides: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantDetailResponse(TenantResponse):
    user_count: int
    listing_count: int


class UpdateTenantRequest(BaseModel):
    name: str | None = None
    plan: str | None = None
    webhook_url: str | None = None


class SetBypassLimitsRequest(BaseModel):
    enabled: bool


class SetPlanOverridesRequest(BaseModel):
    # None clears all overrides; empty dict is rejected as a no-op at the endpoint.
    overrides: dict | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_user(cls, user):
        return cls(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            name=user.name,
            role=user.role.value if hasattr(user.role, 'value') else user.role,
            created_at=user.created_at,
        )


class UpdateUserRoleRequest(BaseModel):
    role: str


class InviteUserRequest(BaseModel):
    email: str
    name: str | None = None
    password: str
    role: str = "operator"


class PlatformStatsResponse(BaseModel):
    total_tenants: int
    total_users: int
    total_listings: int
    listings_by_state: dict[str, int]


class CreditTransactionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    amount: int
    balance_after: int
    transaction_type: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantCreditsResponse(BaseModel):
    tenant_id: uuid.UUID
    credit_balance: int
    transactions: list[CreditTransactionResponse]


class AdjustCreditsRequest(BaseModel):
    amount: int
    reason: str


class CreditSummaryResponse(BaseModel):
    total_credits_outstanding: int
    credits_purchased_this_month: int
    credits_used_this_month: int
    credits_adjusted_this_month: int
    tenant_count_with_credits: int


class RevenueBreakdownResponse(BaseModel):
    subscription_tenant_count: int
    credit_purchase_count: int
    total_credits_purchased: int
    top_tenants_by_usage: list[dict]
    avg_credits_per_listing: float | None


class AdminListingResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    address: dict
    metadata: dict
    state: str
    analysis_tier: str
    credit_cost: int | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class AdminUpdateListingRequest(BaseModel):
    address: dict | None = None
    metadata: dict | None = None
    state: str | None = None


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    email: str
    name: str | None
    role: str
    created_at: datetime


class SystemEventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    listing_id: uuid.UUID | None
    event_type: str
    payload: dict
    created_at: datetime

    model_config = {"from_attributes": True}
