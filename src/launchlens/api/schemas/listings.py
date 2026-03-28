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


class VideoUploadRequest(BaseModel):
    s3_key: str
    video_type: str = "user_raw"
    duration_seconds: int | None = None


class ListingStateResponse(BaseModel):
    listing_id: uuid.UUID
    state: str


class DollhouseResponse(BaseModel):
    scene_json: dict
    room_count: int | None
    created_at: str


class PackageSelectionItem(BaseModel):
    asset_id: str
    channel: str
    position: int
    composite_score: float | None = None
    selected_by: str | None = None


class VideoResponse(BaseModel):
    s3_key: str
    video_type: str
    duration_seconds: int | None = None
    status: str
    chapters: list | None = None
    social_cuts: list | None = None
    thumbnail_s3_key: str | None = None
    clip_count: int | None = None
    created_at: str


class VideoUploadResponse(BaseModel):
    id: str
    s3_key: str
    video_type: str
    status: str


class ActivityEventResponse(BaseModel):
    id: str
    event_type: str
    payload: dict | None = None
    created_at: str
