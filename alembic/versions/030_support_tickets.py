"""Add support tickets and messages tables.

Revision ID: 030_support_tickets
Revises: 029_auto_approve_and_review_metrics
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "030_support_tickets"
down_revision = "029_auto_approve_and_review_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ticket_category = sa.Enum("billing", "technical", "listing", "account", "other", name="ticketcategory")
    ticket_priority = sa.Enum("low", "normal", "high", "urgent", name="ticketpriority")
    ticket_status = sa.Enum("open", "in_progress", "resolved", "closed", name="ticketstatus")

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False, index=True),
        sa.Column("user_id", sa.UUID(), nullable=False, index=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("category", ticket_category, nullable=False, server_default="other"),
        sa.Column("priority", ticket_priority, nullable=False, server_default="normal"),
        sa.Column("status", ticket_status, nullable=False, server_default="open"),
        sa.Column("assigned_to", sa.UUID(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("chat_session_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_created_at", "support_tickets", ["created_at"])

    op.create_table(
        "support_messages",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("ticket_id", sa.UUID(), nullable=False, index=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_admin_reply", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("support_messages")
    op.drop_table("support_tickets")
    sa.Enum(name="ticketcategory").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ticketpriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ticketstatus").drop(op.get_bind(), checkfirst=True)
