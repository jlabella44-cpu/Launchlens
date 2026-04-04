"""Support ticket and message models."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base

from .base import TenantScopedModel


class TicketCategory(str, enum.Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    LISTING = "listing"
    ACCOUNT = "account"
    OTHER = "other"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicket(TenantScopedModel):
    __tablename__ = "support_tickets"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[TicketCategory] = mapped_column(
        SAEnum(TicketCategory, values_callable=lambda x: [e.value for e in x]),
        default=TicketCategory.OTHER,
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, values_callable=lambda x: [e.value for e in x]),
        default=TicketPriority.NORMAL,
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, values_callable=lambda x: [e.value for e in x]),
        default=TicketStatus.OPEN,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict | None] = mapped_column(JSONB, name="metadata", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
