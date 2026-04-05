import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.models.base import TenantScopedModel


class ListingMicrosite(TenantScopedModel):
    __tablename__ = "listing_microsites"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    qr_code_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    microsite_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
