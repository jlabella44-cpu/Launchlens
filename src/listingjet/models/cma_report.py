import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.models.base import TenantScopedModel


class CMAReport(TenantScopedModel):
    __tablename__ = "cma_reports"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    subject_address: Mapped[dict] = mapped_column(JSONB, nullable=False)
    comparables: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    analysis_summary: Mapped[str] = mapped_column(String(5000), nullable=True)
    pdf_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    comparables_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
