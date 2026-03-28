import uuid

from sqlalchemy import UUID, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class PackageSelection(TenantScopedModel):
    __tablename__ = "package_selections"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int | None]
    selected_by: Mapped[str] = mapped_column(String(20), default="ai")
    composite_score: Mapped[float | None]
