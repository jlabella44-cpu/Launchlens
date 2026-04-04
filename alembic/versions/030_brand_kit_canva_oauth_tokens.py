"""add Canva OAuth token columns to brand_kits

Stores per-tenant Canva access/refresh tokens, expiry, and Canva user ID
for the OAuth2 PKCE integration.

Revision ID: 030
Revises: 029
Create Date: 2026-04-03

"""
import sqlalchemy as sa

from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brand_kits", sa.Column("canva_access_token", sa.Text(), nullable=True))
    op.add_column("brand_kits", sa.Column("canva_refresh_token", sa.Text(), nullable=True))
    op.add_column(
        "brand_kits",
        sa.Column("canva_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("brand_kits", sa.Column("canva_user_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("brand_kits", "canva_user_id")
    op.drop_column("brand_kits", "canva_token_expires_at")
    op.drop_column("brand_kits", "canva_refresh_token")
    op.drop_column("brand_kits", "canva_access_token")
