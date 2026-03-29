import uuid

from sqlalchemy import UUID, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class Asset(TenantScopedModel):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "listing_id IS NOT NULL OR api_request_id IS NOT NULL",
            name="asset_must_have_context",
        ),
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    api_request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    file_path: Mapped[str]
    file_hash: Mapped[str]  # SHA-256
    required_for_mls: Mapped[bool] = mapped_column(default=False)
    state: Mapped[str] = mapped_column(String(50), default="uploaded")
