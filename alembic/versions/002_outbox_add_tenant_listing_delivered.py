"""outbox add tenant_id, listing_id, delivered_at

Revision ID: 002
Revises: 001
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outbox",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "outbox",
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "outbox",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Make tenant_id non-nullable after backfill (no existing rows in test DB)
    op.alter_column("outbox", "tenant_id", nullable=False)


def downgrade() -> None:
    op.drop_column("outbox", "delivered_at")
    op.drop_column("outbox", "listing_id")
    op.drop_column("outbox", "tenant_id")
