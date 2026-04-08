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
    page_name: str | None = None
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


# -- Scheduled Post Schemas --

class PublishRequest(BaseModel):
    platform: str = Field(..., pattern="^(instagram|facebook|tiktok)$")
    caption: str = Field(..., min_length=1, max_length=2200)
    hashtags: list[str] = Field(default_factory=list)
    media_s3_keys: list[str] = Field(default_factory=list)


class ScheduleRequest(PublishRequest):
    scheduled_at: datetime


class ScheduledPostResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    platform: str
    caption: str
    hashtags: list[str] = []
    status: str
    scheduled_at: datetime | None = None
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    published_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}


class OAuthRedirectResponse(BaseModel):
    auth_url: str
