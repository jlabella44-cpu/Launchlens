import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from listingjet.models.pipeline_job import JobStatus, PipelineJob


def test_job_status_values():
    assert {s.value for s in JobStatus} == {
        "queued", "waiting", "running", "done", "failed", "skipped", "cancelled",
    }


@pytest.mark.asyncio
async def test_pipeline_job_defaults_and_unique_step(db_session):
    listing_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    job = PipelineJob(tenant_id=tenant_id, listing_id=listing_id, step="ingestion")
    db_session.add(job)
    await db_session.flush()

    row = (await db_session.execute(select(PipelineJob).where(PipelineJob.id == job.id))).scalar_one()
    assert row.status == JobStatus.QUEUED
    assert row.attempts == 0
    assert row.max_attempts == 3
    assert row.run_after is not None
    assert row.payload == {}
    assert row.result is None
    assert row.locked_by is None

    db_session.add(PipelineJob(tenant_id=tenant_id, listing_id=listing_id, step="ingestion"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
