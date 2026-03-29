import enum
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from launchlens.database import Base


class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"  # platform-level: can manage all tenants
    ADMIN = "admin"            # tenant-level: manages own tenant
    OPERATOR = "operator"
    AGENT = "agent"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.OPERATOR)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
