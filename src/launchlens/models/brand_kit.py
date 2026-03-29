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
    canva_template_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice_samples: Mapped[list] = mapped_column(JSONB, default=list)
    raw_config: Mapped[dict] = mapped_column(JSONB, default=dict)
