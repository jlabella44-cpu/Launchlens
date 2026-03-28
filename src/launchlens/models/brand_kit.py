from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class BrandKit(TenantScopedModel):
    __tablename__ = "brand_kits"
    logo_url: Mapped[str | None]
    primary_color: Mapped[str | None] = mapped_column(String(7))
    secondary_color: Mapped[str | None] = mapped_column(String(7))
    font_primary: Mapped[str | None]
    agent_name: Mapped[str | None]
    brokerage_name: Mapped[str | None]
    raw_config: Mapped[dict] = mapped_column(JSONB, default=dict)
