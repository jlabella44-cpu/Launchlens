import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class PhotoOutcomeCorrelation(Base):
    """Aggregated correlation between photo attributes and listing outcomes.

    Computed by OutcomeTracker.compute_correlations() across all closed
    listings for a tenant.  Used by WeightManager to boost/penalize
    room types and photo features based on real sale performance.
    """

    __tablename__ = "photo_outcome_correlations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dimension", "dimension_value", name="uq_poc_tenant_dim_val"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)  # room_label, hero_room, quality_bucket, position_bucket
    dimension_value: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "kitchen", "exterior", "high", "top_5"
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_dom: Mapped[float | None] = mapped_column(Float, nullable=True)  # avg days on market
    avg_price_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_outcome_grade: Mapped[float | None] = mapped_column(Float, nullable=True)  # A=4, B=3, C=2, D=1, F=0
    outcome_boost: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")  # multiplier for WeightManager
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
