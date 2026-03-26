import uuid
from datetime import datetime
from sqlalchemy import UUID, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from launchlens.database import Base


class TenantScopedModel(Base):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
