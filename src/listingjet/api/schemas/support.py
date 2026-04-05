"""Pydantic schemas for the support ticket system."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TicketCreateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=5000)
    category: str = Field(default="other")
    priority: str = Field(default="normal")


class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    content: str
    is_admin_reply: bool
    created_at: datetime
    user_name: str | None = None
    user_email: str | None = None
    chat_transcript: list[dict] | None = None


class TicketResponse(BaseModel):
    id: uuid.UUID
    subject: str
    category: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    user_email: str | None = None
    user_name: str | None = None
    chat_session_id: str | None = None
    resolution_note: str | None = None


class TicketDetailResponse(TicketResponse):
    messages: list[MessageResponse] = []


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int


class AdminTicketUpdateRequest(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    resolution_note: str | None = None


class AdminTicketStatsResponse(BaseModel):
    open_count: int
    in_progress_count: int
    resolved_today: int
    avg_response_hours: float | None
