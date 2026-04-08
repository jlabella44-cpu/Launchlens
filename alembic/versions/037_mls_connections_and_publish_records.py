"""Add MLS connections and publish records tables for RESO Web API certification.

Revision ID: 037_mls_reso
Revises: 036_support_tickets
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "037_mls_reso"
down_revision = "036_support_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- MLS Connections (per-tenant RESO API credentials) --
    op.create_table(
        "mls_connections",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("mls_board", sa.String(255), nullable=False),
        sa.Column("reso_api_url", sa.String(500), nullable=False),
        sa.Column("oauth_token_url", sa.String(500), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("client_secret_encrypted", sa.String(500), nullable=False),
        sa.Column("bearer_token_encrypted", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(50), nullable=True),
        sa.Column("config", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # RLS policy for mls_connections
    op.execute(
        "ALTER TABLE mls_connections ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY tenant_isolation ON mls_connections "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )

    # -- MLS Publish Records (per-listing publish attempts) --
    publish_status = postgresql.ENUM(
        "pending", "submitting_property", "submitting_media",
        "submitted", "confirmed", "failed", "retrying",
        name="publishstatus",
        create_type=False,
    )
    publish_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "mls_publish_records",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(as_uuid=True), sa.ForeignKey("listings.id"), nullable=False, index=True),
        sa.Column("connection_id", sa.UUID(as_uuid=True), sa.ForeignKey("mls_connections.id"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "submitting_property", "submitting_media",
                "submitted", "confirmed", "failed", "retrying",
                name="publishstatus",
                create_type=False,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("reso_listing_key", sa.String(255), nullable=True),
        sa.Column("reso_property_id", sa.String(255), nullable=True),
        sa.Column("photos_submitted", sa.Integer, server_default="0"),
        sa.Column("photos_accepted", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("audit_log", postgresql.JSONB, server_default="[]", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # RLS policy for mls_publish_records
    op.execute(
        "ALTER TABLE mls_publish_records ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY tenant_isolation ON mls_publish_records "
        "USING (tenant_id = current_setting('app.current_tenant')::uuid)"
    )

    # Add PUBLISHING state to listing state enum
    op.execute("ALTER TYPE listingstate ADD VALUE IF NOT EXISTS 'publishing' AFTER 'exporting'")


def downgrade() -> None:
    op.drop_table("mls_publish_records")
    op.execute("DROP TYPE IF EXISTS publishstatus")
    op.drop_table("mls_connections")
    # Note: cannot remove enum value from listingstate in downgrade
