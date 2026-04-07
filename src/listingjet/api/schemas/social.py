"""Schemas for social features: listing events, notifications, social accounts."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CreateListingEventRequest(BaseModel):
    event_type: str = Field(..., pattern="^(open_house|sold_pending)$")
    event_data: dict = Field(default_factory=dict)


class ListingEventResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    event_type: str
    event_data: dict
    notified_at: datetime | None = None
    posted_platforms: list[str] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class MarkPostedRequest(BaseModel):
    platform: str = Field(..., pattern="^(instagram|facebook|tiktok)$")


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str
    action_url: str | None = None
    read_at: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


class CreateSocialAccountRequest(BaseModel):
    platform: str = Field(..., pattern="^(instagram|facebook|tiktok)$")
    platform_username: str = Field(..., min_length=1, max_length=100)


class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    platform: str
    platform_username: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}
