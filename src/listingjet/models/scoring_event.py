import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class ScoringEvent(Base):
    """Logs (features, score, outcome) for each photo scored by PackagingAgent.

    Outcome is backfilled when the user approves, rejects, or swaps.
    This table is the training dataset for the Phase 2 XGBoost model.
    """

    __tablename__ = "scoring_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    room_label: Mapped[str | None] = mapped_column(String(100))
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    position: Mapped[int | None]  # final rank in package (0=hero)
    outcome: Mapped[str | None] = mapped_column(String(20))  # approval, rejection, swap_to, swap_from
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
