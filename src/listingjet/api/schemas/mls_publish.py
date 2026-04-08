"""Pydantic schemas for MLS publish and RESO connection endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# -- MLS Connection schemas --


class CreateMLSConnectionRequest(BaseModel):
    name: str = Field(max_length=255, description="Display name for this connection")
    mls_board: str = Field(max_length=255, description="MLS board name (e.g. 'CRMLS', 'Bright MLS')")
    reso_api_url: str = Field(max_length=500, description="RESO Web API base URL")
    oauth_token_url: str = Field(max_length=500, description="OAuth2 token endpoint URL")
    client_id: str = Field(max_length=255, description="OAuth2 client ID")
    client_secret: str = Field(max_length=255, description="OAuth2 client secret")
    bearer_token: str | None = Field(
        default=None, max_length=500, description="Static bearer token (alternative to OAuth2)"
    )
    config: dict = Field(default_factory=dict, description="Board-specific configuration overrides")


class UpdateMLSConnectionRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    mls_board: str | None = Field(default=None, max_length=255)
    reso_api_url: str | None = Field(default=None, max_length=500)
    oauth_token_url: str | None = Field(default=None, max_length=500)
    client_id: str | None = Field(default=None, max_length=255)
    client_secret: str | None = Field(default=None, max_length=255)
    bearer_token: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    config: dict | None = None


class MLSConnectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    mls_board: str
    reso_api_url: str
    oauth_token_url: str
    client_id: str
    is_active: bool
    last_tested_at: datetime | None
    last_test_status: str | None
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    connection_id: uuid.UUID
    status: str
    error: str | None = None
    tested_at: datetime


# -- MLS Publish schemas --


class PublishRequest(BaseModel):
    connection_id: uuid.UUID | None = Field(
        default=None,
        description="Specific MLS connection to use. Defaults to tenant's active connection.",
    )


class PublishResponse(BaseModel):
    publish_record_id: uuid.UUID
    listing_id: uuid.UUID
    status: str
    message: str


class PublishStatusResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    connection_id: uuid.UUID
    connection_name: str | None = None
    status: str
    reso_listing_key: str | None
    reso_property_id: str | None
    photos_submitted: int
    photos_accepted: int
    error_message: str | None
    error_code: str | None
    retry_count: int
    submitted_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
