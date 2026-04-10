from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class BrandKit(TenantScopedModel):
    __tablename__ = "brand_kits"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_brand_kits_tenant_id"),)
    logo_url: Mapped[str | None]
    primary_color: Mapped[str | None] = mapped_column(String(7))
    secondary_color: Mapped[str | None] = mapped_column(String(7))
    font_primary: Mapped[str | None]
    agent_name: Mapped[str | None]
    brokerage_name: Mapped[str | None]
    canva_template_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice_samples: Mapped[list] = mapped_column(JSONB, default=list)
    raw_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Canva OAuth2 per-tenant tokens
    canva_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    canva_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    canva_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    canva_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # White-label settings (Team/Enterprise)
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    white_label_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    app_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    login_bg_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_header_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    email_footer_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    powered_by_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
