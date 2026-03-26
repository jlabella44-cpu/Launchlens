import uuid
from datetime import datetime
from sqlalchemy import UUID, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from launchlens.database import Base


class VisionResult(Base):
    __tablename__ = "vision_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tier: Mapped[int] = mapped_column(nullable=False)
    room_label: Mapped[str | None] = mapped_column(String(100))
    is_interior: Mapped[bool | None]
    quality_score: Mapped[int | None]
    commercial_score: Mapped[int | None]
    hero_candidate: Mapped[bool | None]
    hero_explanation: Mapped[str | None]
    raw_labels: Mapped[dict | None] = mapped_column(JSONB)
    model_used: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
