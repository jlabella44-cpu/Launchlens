"""Track each MLS publish attempt for a listing."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class PublishStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTING_PROPERTY = "submitting_property"
    SUBMITTING_MEDIA = "submitting_media"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    RETRYING = "retrying"


class MLSPublishRecord(TenantScopedModel):
    __tablename__ = "mls_publish_records"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mls_connections.id"), nullable=False
    )

    status: Mapped[PublishStatus] = mapped_column(
        SAEnum(PublishStatus, values_callable=lambda x: [e.value for e in x]),
        default=PublishStatus.PENDING,
        nullable=False,
    )

    # RESO-assigned identifiers after successful submission
    reso_listing_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reso_property_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Counts
    photos_submitted: Mapped[int] = mapped_column(Integer, default=0)
    photos_accepted: Mapped[int] = mapped_column(Integer, default=0)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Full request/response log for audit
    audit_log: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
