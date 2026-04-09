import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Float, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class TenantHealthWeights(Base):
    """Per-tenant custom health score weights (Enterprise/Team only)."""

    __tablename__ = "tenant_health_weights"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_thw_tenant"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    media: Mapped[float] = mapped_column(Float, nullable=False, default=0.30)
    content: Mapped[float] = mapped_column(Float, nullable=False, default=0.20)
    velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.15)
    syndication: Mapped[float] = mapped_column(Float, nullable=False, default=0.20)
    market: Mapped[float] = mapped_column(Float, nullable=False, default=0.15)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
