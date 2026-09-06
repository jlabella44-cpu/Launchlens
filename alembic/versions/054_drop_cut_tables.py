"""drop cut-feature tables: cma_reports, idx_feed_configs, api_keys

Revision ID: 054_drop_cut_tables
Revises: 053_pipeline_jobs
"""
from alembic import op

revision = "054_drop_cut_tables"
down_revision = "053_pipeline_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("cma_reports", "idx_feed_configs", "api_keys"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def downgrade() -> None:
    # Irreversible by design: the features were removed. Recreate from the
    # original migrations (cma: 032_add_cma_reports_table; idx: 041_health_score_and_idx_feed; api_keys: 009_api_keys) if ever needed.
    raise RuntimeError("054_drop_cut_tables cannot be downgraded")
