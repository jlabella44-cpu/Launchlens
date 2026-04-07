"""Social features: listing_events, social_accounts, notifications tables.

Revision ID: 040
Revises: 039_add_draft_state_and_bundle
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "040"
down_revision = "039_add_draft_state_and_bundle"


def upgrade():
    op.create_table(
        "listing_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("listing_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("followup_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_platforms", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "social_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("platform_username", sa.String(100), nullable=False),
        sa.Column("platform_user_id", sa.String(255), nullable=True),
        sa.Column("access_token_encrypted", sa.String(500), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "platform", name="uq_social_accounts_user_platform"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.String(1000), nullable=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "read_at"])


def downgrade():
    op.drop_table("notifications")
    op.drop_table("social_accounts")
    op.drop_table("listing_events")
