"""add listing_microsites table

Revision ID: 033
Revises: 032
Create Date: 2026-04-04

"""
import sqlalchemy as sa

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listing_microsites",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("qr_code_s3_key", sa.String(500), nullable=True),
        sa.Column("microsite_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), server_default="ready"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("listing_microsites")
