"""CreditTransaction — tracks credit additions, deductions, adjustments, and expirations."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import UUID, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from launchlens.database import Base


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # positive = add, negative = deduct
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # purchase, usage, admin_adjustment, expiration, bonus
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
