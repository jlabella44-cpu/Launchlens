import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from launchlens.database import Base


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    plan_tier: Mapped[str] = mapped_column(String(50), default="lite")
    billing_model: Mapped[str] = mapped_column(String(50), default="credit")
    per_listing_credit_cost: Mapped[int] = mapped_column(Integer, default=1)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Credit system
    credit_balance: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    included_credits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rollover_cap: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
