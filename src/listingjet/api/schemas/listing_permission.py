import uuid
from datetime import datetime
from pydantic import BaseModel


class ShareListingRequest(BaseModel):
    email: str  # grantee email — looks up user by email
    permission: str = "read"  # read, write, publish, billing
    expires_at: datetime | None = None


class ListingPermissionResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID | None
    grantee_user_id: uuid.UUID
    grantee_email: str  # denormalized for display
    grantee_name: str | None
    permission: str
    expires_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class UpdatePermissionRequest(BaseModel):
    permission: str | None = None
    expires_at: datetime | None = None


class AuditLogEntryResponse(BaseModel):
    id: uuid.UUID
    user_email: str
    user_name: str | None
    action: str
    details: dict = {}
    created_at: datetime
    model_config = {"from_attributes": True}
