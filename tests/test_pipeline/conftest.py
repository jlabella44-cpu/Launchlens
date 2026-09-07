import pytest
from sqlalchemy import delete

from listingjet.models.pipeline_job import PipelineJob


@pytest.fixture(autouse=True)
async def _clean_pipeline_jobs(db_session):
    """claim_next/run_job commit on the shared test session, so rows outlive the
    per-test rollback. Wipe the table before every pipeline test so a crashed
    earlier run cannot leave a claimable job behind."""
    await db_session.execute(delete(PipelineJob))
    await db_session.commit()
    yield
