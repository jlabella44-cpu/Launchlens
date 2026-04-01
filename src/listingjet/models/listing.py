import enum
import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class ListingState(str, enum.Enum):
    NEW = "new"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    AWAITING_REVIEW = "awaiting_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DELIVERED = "delivered"
    PIPELINE_TIMEOUT = "pipeline_timeout"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPORTING = "exporting"
    DEMO = "demo"


class Listing(TenantScopedModel):
    __tablename__ = "listings"
    address: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_: Mapped[dict] = mapped_column(JSONB, name="metadata", nullable=False, default=dict)
    state: Mapped[ListingState] = mapped_column(SAEnum(ListingState, values_callable=lambda x: [e.value for e in x]), default=ListingState.NEW, nullable=False)
    analysis_tier: Mapped[str] = mapped_column(String(20), default="standard")
    lock_owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    mls_bundle_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    marketing_bundle_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    credit_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    demo_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
