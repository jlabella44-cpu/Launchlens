import uuid
from datetime import datetime

from pydantic import BaseModel


class AddonResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    credit_cost: int
    is_active: bool

    model_config = {"from_attributes": True}


class AddonPurchaseResponse(BaseModel):
    id: uuid.UUID
    addon_id: uuid.UUID
    addon_slug: str
    addon_name: str
    status: str
    created_at: datetime


class ActivateAddonRequest(BaseModel):
    addon_slug: str
