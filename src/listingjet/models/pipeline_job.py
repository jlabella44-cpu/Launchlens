"""One row per (listing, pipeline step). The worker loop claims rows with
SELECT ... FOR UPDATE SKIP LOCKED; see listingjet.pipeline.runner.

This table has row-level security (tenant_isolation policy, migration 053).
The worker is a system actor that claims jobs across all tenants, so any
session it uses to read/write PipelineJob rows must run in an admin context
(SET LOCAL app.is_admin = 'true'); a plain tenant-scoped session will only
see/affect rows for its own tenant_id."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from listingjet.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "queued"       # runnable once prerequisites are satisfied
    WAITING = "waiting"     # human gate; completed by an API call, never by the worker
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"     # gated off (add-on / billing) — counts as satisfied
    CANCELLED = "cancelled" # listing failed or was cancelled before this ran


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"
    __table_args__ = (UniqueConstraint("listing_id", "step", name="uq_pipeline_jobs_listing_step"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="pipeline_job_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=JobStatus.QUEUED, index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
