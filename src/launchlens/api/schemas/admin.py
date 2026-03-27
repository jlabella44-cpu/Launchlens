import uuid
from datetime import datetime
from pydantic import BaseModel


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantDetailResponse(TenantResponse):
    user_count: int
    listing_count: int


class UpdateTenantRequest(BaseModel):
    name: str | None = None
    plan: str | None = None


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
