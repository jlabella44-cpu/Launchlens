import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class ListingOutcome(TenantScopedModel):
    """Records the final sale outcome for a delivered listing.

    Populated by the IDX feed poller when a listing transitions to
    Pending (under contract) or Closed (sold).  Correlates with
    PackageSelection rows to measure which photo choices drive results.
    """

    __tablename__ = "listing_outcomes"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # active, pending, closed, expired, withdrawn
    list_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # sale / list
    days_on_market: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_to_contract: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_changes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_photos_mls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hero_room_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avg_photo_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_grade: Mapped[str | None] = mapped_column(String(1), nullable=True)  # A, B, C, D, F
    idx_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_idx_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
