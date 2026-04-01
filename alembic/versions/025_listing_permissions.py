"""add listing_permissions and listing_audit_log tables

Revision ID: 025
Revises: 024
Create Date: 2026-04-01

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listing_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("grantee_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grantee_tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("grantor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("grantor_tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("permission", sa.Text(), nullable=False, server_default="read"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("permission IN ('read', 'write', 'publish', 'billing')", name="ck_lp_permission"),
    )

    op.create_index("idx_lp_listing", "listing_permissions", ["listing_id"], postgresql_where=sa.text("revoked_at IS NULL"))
    op.create_index("idx_lp_grantee", "listing_permissions", ["grantee_user_id"], postgresql_where=sa.text("revoked_at IS NULL"))
    op.create_index("idx_lp_agent", "listing_permissions", ["agent_user_id"], postgresql_where=sa.text("revoked_at IS NULL"))

    op.create_table(
        "listing_audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_email", sa.Text(), nullable=False),
        sa.Column("user_name", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("details", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("idx_audit_listing", "listing_audit_log", ["listing_id", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_table("listing_audit_log")
    op.drop_table("listing_permissions")
