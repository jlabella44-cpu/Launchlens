"""add proxy_path column to assets for AI analysis proxies

Revision ID: 026
Revises: 025
Create Date: 2026-04-02

"""
import sqlalchemy as sa

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("proxy_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "proxy_path")
