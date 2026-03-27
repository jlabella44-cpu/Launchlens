import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class SocialContent(TenantScopedModel):
    __tablename__ = "social_contents"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cta: Mapped[str | None] = mapped_column(String(500), nullable=True)
