"""Notification preference schemas."""

from pydantic import BaseModel


class NotificationPreferenceResponse(BaseModel):
    email_on_complete: bool = True
    email_on_failure: bool = True
    email_on_review_ready: bool = True

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    email_on_complete: bool | None = None
    email_on_failure: bool | None = None
    email_on_review_ready: bool | None = None
