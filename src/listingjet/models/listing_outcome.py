import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class ListingOutcome(TenantScopedModel):
    """Materialized outcome snapshot per delivered listing — updated by IDX poller."""

    __tablename__ = "listing_outcomes"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    days_on_market: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    sold_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Photo metrics at delivery time
    avg_photo_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_commercial_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hero_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    photo_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_diversity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_score_at_delivery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
