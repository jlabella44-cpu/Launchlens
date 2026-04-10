import enum
import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


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
    # Nullable while an invitation is pending — set on accept.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.OPERATOR)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_consent_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Team invitation fields. Populated on invite, cleared on accept.
    invite_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
