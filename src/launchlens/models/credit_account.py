"""Credit account model for tracking per-tenant credit balances."""
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from launchlens.database import Base


class CreditAccount(Base):
    __tablename__ = "credit_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    included_credits: Mapped[int] = mapped_column(Integer, default=0)
    rollover_cap: Mapped[int] = mapped_column(Integer, default=5)
    per_listing_credit_cost: Mapped[int] = mapped_column(Integer, default=1)
    tier: Mapped[str] = mapped_column(String(50), default="lite")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
