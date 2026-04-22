import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    plan_tier: Mapped[str] = mapped_column(String(50), default="free")
    billing_model: Mapped[str] = mapped_column(String(50), default="credit")
    per_listing_credit_cost: Mapped[int] = mapped_column(Integer, default=12)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    included_credits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rollover_cap: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    # Review settings
    auto_approve_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    auto_approve_threshold: Mapped[float] = mapped_column(Float, default=85.0, server_default="85.0")
    # Admin controls (migration 050)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bypass_limits: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    plan_overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
