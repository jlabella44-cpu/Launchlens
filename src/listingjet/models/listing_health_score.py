import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class ListingHealthScore(TenantScopedModel):
    """Latest health score snapshot per listing — upserted on each recalculation."""

    __tablename__ = "listing_health_scores"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    media_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    velocity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    syndication_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    market_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    signals_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
