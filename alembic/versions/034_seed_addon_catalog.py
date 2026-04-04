"""seed addon catalog with virtual_staging, image_editing, cma_report

Revision ID: 034
Revises: 033
Create Date: 2026-04-04

"""
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO addon_catalog (id, slug, name, credit_cost, is_active, metadata)
        VALUES
            (gen_random_uuid(), 'virtual_staging', 'Virtual Staging', 15, true, '{"styles": ["modern", "contemporary", "minimalist", "coastal", "traditional", "luxury"]}'),
            (gen_random_uuid(), 'image_editing', 'AI Image Editing', 5, true, '{"capabilities": ["remove_object", "enhance", "auto_fix_compliance"]}'),
            (gen_random_uuid(), 'cma_report', 'CMA Report', 10, true, '{"format": "html"}')
        ON CONFLICT (slug) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM addon_catalog WHERE slug IN ('virtual_staging', 'image_editing', 'cma_report')")
