"""vision_results analysis columns

Revision ID: 055_vision_result_analysis
Revises: 054_drop_cut_tables
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "055_vision_result_analysis"
down_revision = "054_drop_cut_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vision_results", sa.Column("hero_score", sa.Integer(), nullable=True))
    op.add_column("vision_results", sa.Column("is_photo", sa.Boolean(), nullable=True))
    op.add_column("vision_results", sa.Column("is_empty_room", sa.Boolean(), nullable=True))
    op.add_column("vision_results", sa.Column("features", postgresql.JSONB(), nullable=True))
    op.add_column("vision_results", sa.Column("compliance", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("vision_results", "compliance")
    op.drop_column("vision_results", "features")
    op.drop_column("vision_results", "is_empty_room")
    op.drop_column("vision_results", "is_photo")
    op.drop_column("vision_results", "hero_score")
