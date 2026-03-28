import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class PerformanceEvent(TenantScopedModel):
    __tablename__ = "performance_events"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float | None]
    source: Mapped[str] = mapped_column(String(100))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
