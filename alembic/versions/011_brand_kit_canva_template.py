"""add canva_template_id to brand_kits

Revision ID: 011
Revises: 010
Create Date: 2026-03-29
"""
import sqlalchemy as sa

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brand_kits", sa.Column("canva_template_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("brand_kits", "canva_template_id")
