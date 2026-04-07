import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class HealthScoreHistory(TenantScopedModel):
    """Rolling 90-day append-only health score history for trend analysis."""

    __tablename__ = "health_score_history"
    __table_args__ = (
        Index("ix_health_history_listing_calc", "listing_id", "calculated_at"),
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    media_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    velocity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    syndication_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    market_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
