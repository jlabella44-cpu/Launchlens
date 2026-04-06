import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    __table_args__ = (UniqueConstraint("tenant_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    granted_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    purchased_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    rollover_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rollover_cap: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
