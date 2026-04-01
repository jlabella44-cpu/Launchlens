"""add property_data table

Revision ID: 023
Revises: 022
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_data",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("address_hash", sa.String(64), nullable=False),
        sa.Column("property_status", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("api_source", sa.String(20), nullable=True),
        sa.Column("api_raw", postgresql.JSONB(), nullable=True),
        sa.Column("beds", sa.Integer(), nullable=True),
        sa.Column("baths", sa.Integer(), nullable=True),
        sa.Column("half_baths", sa.Integer(), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("lot_sqft", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("property_type", sa.String(30), nullable=True),
        sa.Column("stories", sa.Integer(), nullable=True),
        sa.Column("garage_spaces", sa.Integer(), nullable=True),
        sa.Column("has_pool", sa.Boolean(), nullable=True),
        sa.Column("has_basement", sa.Boolean(), nullable=True),
        sa.Column("heating_type", sa.String(50), nullable=True),
        sa.Column("cooling_type", sa.String(50), nullable=True),
        sa.Column("roof_type", sa.String(50), nullable=True),
        sa.Column("hoa_monthly", sa.Float(), nullable=True),
        sa.Column("walk_score", sa.Integer(), nullable=True),
        sa.Column("transit_score", sa.Integer(), nullable=True),
        sa.Column("bike_score", sa.Integer(), nullable=True),
        sa.Column("nearby_amenities", postgresql.JSONB(), nullable=True),
        sa.Column("school_ratings", postgresql.JSONB(), nullable=True),
        sa.Column("lifestyle_tags", postgresql.JSONB(), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("field_confidence", postgresql.JSONB(), nullable=True),
        sa.Column("mismatches", postgresql.JSONB(), nullable=True),
        sa.Column("scraped_data", postgresql.JSONB(), nullable=True),
        sa.Column("sources_checked", postgresql.JSONB(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id"),
    )
    op.create_index("ix_property_data_listing_id", "property_data", ["listing_id"])
    op.create_index("ix_property_data_address_hash", "property_data", ["address_hash"])


def downgrade() -> None:
    op.drop_index("ix_property_data_address_hash", table_name="property_data")
    op.drop_index("ix_property_data_listing_id", table_name="property_data")
    op.drop_table("property_data")
