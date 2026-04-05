"""Add auto-approval settings to tenants and review metrics to package_selections.

Revision ID: 035_auto_approve
Revises: 034
"""

from alembic import op
import sqlalchemy as sa

revision = "035_auto_approve"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("auto_approve_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("tenants", sa.Column("auto_approve_threshold", sa.Float(), server_default="85.0", nullable=False))


def downgrade() -> None:
    op.drop_column("tenants", "auto_approve_threshold")
    op.drop_column("tenants", "auto_approve_enabled")
