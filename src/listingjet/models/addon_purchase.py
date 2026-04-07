import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class AddonPurchase(Base):
    __tablename__ = "addon_purchases"
    __table_args__ = (UniqueConstraint("listing_id", "addon_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    addon_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    credit_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, refunded, completed
    bundle_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
