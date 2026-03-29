import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class LearningWeight(Base):
    __tablename__ = "learning_weights"
    __table_args__ = (UniqueConstraint("tenant_id", "room_label"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    room_label: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(default=1.0)
    labeled_listing_count: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
