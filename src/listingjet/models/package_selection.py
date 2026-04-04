import uuid

from sqlalchemy import UUID, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class PackageSelection(TenantScopedModel):
    __tablename__ = "package_selections"
    __table_args__ = (
        UniqueConstraint("listing_id", "channel", "position", name="uq_package_selections_listing_channel_position"),
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int | None]
    selected_by: Mapped[str] = mapped_column(String(20), default="ai")
    composite_score: Mapped[float | None]
