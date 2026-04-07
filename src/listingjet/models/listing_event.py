import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class ListingEvent(TenantScopedModel):
    __tablename__ = "listing_events"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followup_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_platforms: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
