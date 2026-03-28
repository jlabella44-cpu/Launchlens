import uuid

from sqlalchemy import UUID, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class VideoAsset(TenantScopedModel):
    __tablename__ = "video_assets"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    video_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ai_generated, user_raw, professional
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="processing")  # uploading, processing, ready, failed
    chapters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # [{"time": 0, "label": "exterior"}, ...]
    social_cuts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # [{"platform": "instagram", "s3_key": "...", "duration": 15}, ...]
    branded_player_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {logo_url, cta_text, accent_color}
    thumbnail_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    clip_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
