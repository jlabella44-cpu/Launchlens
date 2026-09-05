"""tenant_id indexes on users, outbox, audit_logs

Revision ID: 052_tenant_indexes
Revises: 051_admin_rls_bypass
"""
from alembic import op

revision = "052_tenant_indexes"
down_revision = "051_admin_rls_bypass"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_outbox_tenant_id", "outbox", ["tenant_id"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_index("ix_outbox_tenant_id", table_name="outbox")
    op.drop_index("ix_users_tenant_id", table_name="users")
