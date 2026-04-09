"""Add AI processing consent fields to users.

Revision ID: 048_ai_consent
Revises: 047_tenant_health_weights
"""

import sqlalchemy as sa

from alembic import op

revision = "048_ai_consent"
down_revision = "047_tenant_health_weights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ai_consent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("ai_consent_version", sa.String(20), nullable=True))

    # Backfill: existing users who accepted ToS also accepted AI processing
    op.execute("UPDATE users SET ai_consent_at = consent_at, ai_consent_version = '1.0' WHERE consent_at IS NOT NULL")


def downgrade() -> None:
    op.drop_column("users", "ai_consent_version")
    op.drop_column("users", "ai_consent_at")
