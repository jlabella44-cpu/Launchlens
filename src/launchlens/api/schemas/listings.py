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
