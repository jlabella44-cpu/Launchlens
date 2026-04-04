"""Add auto-approval settings to tenants and review metrics to package_selections.

Revision ID: 029_auto_approve_and_review_metrics
Revises: 028_add_user_consent_fields
"""

from alembic import op
import sqlalchemy as sa

revision = "029_auto_approve_and_review_metrics"
down_revision = "028_add_user_consent_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("auto_approve_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("tenants", sa.Column("auto_approve_threshold", sa.Float(), server_default="85.0", nullable=False))


def downgrade() -> None:
    op.drop_column("tenants", "auto_approve_threshold")
    op.drop_column("tenants", "auto_approve_enabled")
