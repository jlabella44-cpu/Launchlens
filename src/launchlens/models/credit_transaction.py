import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from launchlens.database import Base


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # purchase, grant, deduction, rollover, expiry
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # stripe_invoice, stripe_event, etc.
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
