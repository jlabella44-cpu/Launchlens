"""Add white-label columns to brand_kits.

Revision ID: 042_white_label
Revises: 041_health_score
"""

import sqlalchemy as sa

from alembic import op

revision = "042_white_label"
down_revision = "041_health_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brand_kits", sa.Column("custom_domain", sa.String(255), nullable=True))
    op.add_column("brand_kits", sa.Column("domain_verified", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("brand_kits", sa.Column("white_label_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("brand_kits", sa.Column("app_name", sa.String(100), nullable=True))
    op.add_column("brand_kits", sa.Column("tagline", sa.String(255), nullable=True))
    op.add_column("brand_kits", sa.Column("favicon_url", sa.String(500), nullable=True))
    op.add_column("brand_kits", sa.Column("login_bg_url", sa.String(500), nullable=True))
    op.add_column("brand_kits", sa.Column("email_header_color", sa.String(7), nullable=True))
    op.add_column("brand_kits", sa.Column("email_footer_text", sa.String(500), nullable=True))
    op.add_column("brand_kits", sa.Column("powered_by_visible", sa.Boolean(), server_default="true", nullable=False))
    op.create_index("ix_brand_kits_custom_domain", "brand_kits", ["custom_domain"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_brand_kits_custom_domain")
    for col in ["powered_by_visible", "email_footer_text", "email_header_color",
                 "login_bg_url", "favicon_url", "tagline", "app_name",
                 "white_label_enabled", "domain_verified", "custom_domain"]:
        op.drop_column("brand_kits", col)
