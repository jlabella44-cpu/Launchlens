import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class ScheduledPost(TenantScopedModel):
    """A social media post — scheduled, in-flight, published, or failed."""

    __tablename__ = "scheduled_posts"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    listing_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    media_s3_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    platform_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform_post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
