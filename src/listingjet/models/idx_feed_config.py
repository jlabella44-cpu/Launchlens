import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class IdxFeedConfig(TenantScopedModel):
    """Per-tenant RESO/IDX feed connection configuration."""

    __tablename__ = "idx_feed_configs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(1000), nullable=False)
    board_id: Mapped[str] = mapped_column(String(100), nullable=True)
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, server_default="60")
    last_polled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
