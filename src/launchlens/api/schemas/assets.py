import uuid
from datetime import datetime
from pydantic import BaseModel


class AssetInput(BaseModel):
    file_path: str
    file_hash: str


class CreateAssetsRequest(BaseModel):
    assets: list[AssetInput]


class CreateAssetsResponse(BaseModel):
    count: int
    listing_state: str


class AssetResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID | None
    file_path: str
    file_hash: str
    state: str
    created_at: datetime

    model_config = {"from_attributes": True}
