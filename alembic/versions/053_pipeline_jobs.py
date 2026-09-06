"""pipeline_jobs table (replaces Temporal)

Revision ID: 053_pipeline_jobs
Revises: 052_tenant_indexes
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "053_pipeline_jobs"
down_revision = "052_tenant_indexes"
branch_labels = None
depends_on = None

_STATUS = ("queued", "waiting", "running", "done", "failed", "skipped", "cancelled")


def upgrade() -> None:
    status_enum = postgresql.ENUM(*_STATUS, name="pipeline_job_status", create_type=False)
    status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "pipeline_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step", sa.String(64), nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_by", sa.String(128), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("listing_id", "step", name="uq_pipeline_jobs_listing_step"),
    )
    op.create_index("ix_pipeline_jobs_tenant_id", "pipeline_jobs", ["tenant_id"])
    op.create_index("ix_pipeline_jobs_listing_id", "pipeline_jobs", ["listing_id"])
    op.create_index("ix_pipeline_jobs_status", "pipeline_jobs", ["status"])
    # The worker's claim query: queued rows ordered by run_after.
    op.create_index("ix_pipeline_jobs_claim", "pipeline_jobs", ["status", "run_after"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_jobs_claim", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_status", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_listing_id", table_name="pipeline_jobs")
    op.drop_index("ix_pipeline_jobs_tenant_id", table_name="pipeline_jobs")
    op.drop_table("pipeline_jobs")
    postgresql.ENUM(name="pipeline_job_status").drop(op.get_bind(), checkfirst=True)
