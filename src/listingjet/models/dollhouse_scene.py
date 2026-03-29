import uuid

from sqlalchemy import UUID, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import TenantScopedModel


class DollhouseScene(TenantScopedModel):
    __tablename__ = "dollhouse_scenes"
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    scene_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    room_count: Mapped[int] = mapped_column(Integer, default=0)
    floorplan_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
