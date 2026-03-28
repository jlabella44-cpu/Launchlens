import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from launchlens.database import Base


class LabelMapping(Base):
    __tablename__ = "label_mappings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    required_labels: Mapped[list] = mapped_column(JSONB, nullable=False)
    optional_labels: Mapped[list] = mapped_column(JSONB, nullable=False)
    room_type: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
