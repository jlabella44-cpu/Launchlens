"""Per-tenant MLS connection credentials for RESO Web API publishing."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class MLSConnection(TenantScopedModel):
    __tablename__ = "mls_connections"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mls_board: Mapped[str] = mapped_column(String(255), nullable=False)
    reso_api_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # OAuth2 client_credentials flow (RESO standard auth)
    oauth_token_url: Mapped[str] = mapped_column(String(500), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)

    # Optional: some MLS boards issue a static bearer token instead of OAuth2
    bearer_token_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Provider-specific config (e.g. board-specific field overrides)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
