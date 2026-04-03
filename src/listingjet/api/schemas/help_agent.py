"""Pydantic schemas for the AI help agent endpoints."""
from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime | None = None
    tools_used: list[str] | None = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., max_length=64)
    message_index: int = Field(..., ge=0)
    rating: str = Field(..., pattern="^(up|down)$")


class FeedbackResponse(BaseModel):
    status: str


class AdminHelpAgentStatsResponse(BaseModel):
    date: str
    total_messages: int
    messages_by_tenant: dict[str, int]
    tool_usage: dict[str, int]
    feedback_summary: dict[str, int]
