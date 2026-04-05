import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AddressPayload(BaseModel):
    """Validated address structure for listings."""
    street: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=50)
    zip: str | None = Field(default=None, max_length=20)
    unit: str | None = Field(default=None, max_length=50)
    country: str = Field(default="US", max_length=10)

    model_config = {"extra": "allow"}


class ListingMetadata(BaseModel):
    """Validated metadata structure for listings.

    Accepts both short names (beds/baths) and long names (bedrooms/bathrooms).
    Extra fields are passed through for extensibility.
    """
    beds: int | None = Field(default=None, ge=0, le=100)
    baths: float | None = Field(default=None, ge=0, le=100)
    sqft: int | None = Field(default=None, ge=0, le=1_000_000)
    price: int | None = Field(default=None, ge=0)
    lot_sqft: int | None = Field(default=None, ge=0, le=100_000_000)
    year_built: int | None = Field(default=None, ge=1600, le=2100)
    property_type: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=5000)

    model_config = {"extra": "allow"}


class CreateListingRequest(BaseModel):
    address: AddressPayload
    metadata: ListingMetadata | None = ListingMetadata()
    idempotency_key: str | None = Field(default=None, max_length=64)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "address": {
                        "street": "123 Main St",
                        "city": "Austin",
                        "state": "TX",
                        "zip": "78701",
                    },
                    "metadata": {"bedrooms": 3, "bathrooms": 2, "sqft": 1850},
                }
            ]
        }
    }


class UpdateListingRequest(BaseModel):
    address: AddressPayload | None = None
    metadata: ListingMetadata | None = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    address: dict
    metadata: dict
    state: str
    thumbnail_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                    "address": {"street": "123 Main St", "city": "Austin", "state": "TX", "zip": "78701"},
                    "metadata": {"bedrooms": 3, "bathrooms": 2, "sqft": 1850},
                    "state": "new",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                }
            ]
        },
    }

    @classmethod
    def from_orm_listing(cls, listing, thumbnail_url: str | None = None):
        return cls(
            id=listing.id,
            tenant_id=listing.tenant_id,
            address=listing.address,
            metadata=listing.metadata_,
            state=listing.state.value if hasattr(listing.state, 'value') else listing.state,
            thumbnail_url=thumbnail_url,
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


class UploadUrlFileItem(BaseModel):
    filename: str
    content_type: str | None = None


class UploadUrlsRequest(BaseModel):
    filenames: list[str] | None = None
    files: list[UploadUrlFileItem | str] | None = None
    content_type: str = "image/jpeg"
