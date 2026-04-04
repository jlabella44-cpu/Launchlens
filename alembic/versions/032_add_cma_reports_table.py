"""add cma_reports table

Revision ID: 032
Revises: 031
Create Date: 2026-04-04

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cma_reports",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("listing_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("subject_address", postgresql.JSONB(), nullable=False),
        sa.Column("comparables", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("analysis_summary", sa.String(5000), nullable=True),
        sa.Column("pdf_s3_key", sa.String(500), nullable=True),
        sa.Column("comparables_count", sa.Integer(), server_default="0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("cma_reports")
