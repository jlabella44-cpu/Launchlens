"""add voice_samples to brand_kits for few-shot brand voice

Revision ID: 013
Revises: 011
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "013"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brand_kits", sa.Column("voice_samples", JSONB(), server_default="[]", nullable=False))


def downgrade() -> None:
    op.drop_column("brand_kits", "voice_samples")
