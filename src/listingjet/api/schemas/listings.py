import enum
import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateListingRequest(BaseModel):
    address: dict
    metadata: dict = {}


class UpdateListingRequest(BaseModel):
    address: dict | None = None
    metadata: dict | None = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    address: dict
    metadata: dict
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_listing(cls, listing):
        return cls(
            id=listing.id,
            tenant_id=listing.tenant_id,
            address=listing.address,
            metadata=listing.metadata_,
            state=listing.state.value if hasattr(listing.state, 'value') else listing.state,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )


class ExportMode(str, enum.Enum):
    mls = "mls"
    marketing = "marketing"


class BundleMetadata(BaseModel):
    photo_count: int | None = None
    includes_description: bool = True
    includes_flyer: bool = False
    includes_social_posts: bool = False


class ExportResponse(BaseModel):
    listing_id: uuid.UUID
    mode: str
    download_url: str
    expires_at: datetime
    bundle: BundleMetadata


class ActionResponse(BaseModel):
    listing_id: str
    state: str


class CancelResponse(BaseModel):
    listing_id: str
    state: str
    credits_refunded: int = 0


class PipelineStepStatus(BaseModel):
    name: str
    status: str
    completed_at: str | None = None
    progress: str | None = None


class PipelineStatusResponse(BaseModel):
    listing_id: str
    listing_state: str
    steps: list[PipelineStepStatus]


class VideoUploadRequest(BaseModel):
    s3_key: str
    video_type: str = "user_raw"
    duration_seconds: int | None = None


class RejectRequest(BaseModel):
    reason: str  # quality, incomplete, non_compliant, other
    detail: str = ""


class ReorderRequest(BaseModel):
    swaps: list[dict]  # [{"asset_id": "...", "new_position": 0}, ...]


class UploadUrlsRequest(BaseModel):
    filenames: list[str]
    content_type: str = "image/jpeg"
