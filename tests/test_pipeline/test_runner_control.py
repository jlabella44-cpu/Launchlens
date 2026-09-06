import uuid

import pytest
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import Step
from tests.test_agents.conftest import make_session_factory

STEPS = [Step("ingestion"), Step("packaging", requires=("ingestion",)),
         Step("await_review", requires=("packaging",), gate="review"),
         Step("content", requires=("await_review",))]


async def _setup(db_session, state=ListingState.UPLOADING):
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Gate St"}, metadata_={}, state=state)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    return listing, make_session_factory(db_session)


async def _status(db_session, listing_id, step):
    return (await db_session.execute(select(PipelineJob.status).where(
        PipelineJob.listing_id == listing_id, PipelineJob.step == step))).scalar_one()


@pytest.mark.asyncio
async def test_complete_review_unblocks_content(db_session):
    listing, factory = await _setup(db_session)
    ok = {"ingestion": lambda ctx: _ret({}), "packaging": lambda ctx: _ret({"auto_approved": False}),
          "content": lambda ctx: _ret({})}
    for _ in range(2):
        job = await runner.claim_next(db_session, "w", steps=STEPS)
        await runner.run_job(factory, job.id, steps=STEPS, functions=ok)
    assert await runner.claim_next(db_session, "w", steps=STEPS) is None  # blocked on the gate
    assert await runner.complete_review(db_session, listing.id) is True
    assert await _status(db_session, listing.id, "await_review") == JobStatus.DONE
    assert (await runner.claim_next(db_session, "w", steps=STEPS)).step == "content"
    assert await runner.complete_review(db_session, listing.id) is False


@pytest.mark.asyncio
async def test_packaging_auto_approve_completes_gate(db_session):
    listing, factory = await _setup(db_session)
    fns = {"ingestion": lambda ctx: _ret({}), "packaging": lambda ctx: _ret({"auto_approved": True})}
    for _ in range(2):
        job = await runner.claim_next(db_session, "w", steps=STEPS)
        await runner.run_job(factory, job.id, steps=STEPS, functions=fns)
    assert await _status(db_session, listing.id, "await_review") == JobStatus.DONE


@pytest.mark.asyncio
async def test_retry_listing_requeues_failed_and_cancelled(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    await runner.run_job(factory, job.id, steps=STEPS, functions={"ingestion": lambda ctx: _raise(ValueError("x"))})
    assert (await db_session.get(Listing, listing.id)).state == ListingState.FAILED
    n = await runner.retry_listing(db_session, listing, steps=STEPS)
    assert n == 3  # ingestion (failed) + packaging + content (cancelled); the gate goes back to waiting
    assert await _status(db_session, listing.id, "ingestion") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "await_review") == JobStatus.WAITING
    assert (await db_session.get(Listing, listing.id)).state == ListingState.UPLOADING


@pytest.mark.asyncio
async def test_cancel_listing_jobs(db_session):
    listing, _ = await _setup(db_session)
    assert await runner.cancel_listing_jobs(db_session, listing.id) == 4
    assert await _status(db_session, listing.id, "content") == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_run_job_ignores_stale_success_after_cancel(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    assert await runner.cancel_listing_jobs(db_session, listing.id) == 4  # all queued/waiting/running jobs
    status = await runner.run_job(factory, job.id, steps=STEPS, functions={"ingestion": lambda ctx: _ret({})})
    assert status == JobStatus.CANCELLED
    assert await _status(db_session, listing.id, "ingestion") == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_run_job_ignores_stale_failure_after_cancel(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    assert await runner.cancel_listing_jobs(db_session, listing.id) == 4
    status = await runner.run_job(factory, job.id, steps=STEPS,
                                  functions={"ingestion": lambda ctx: _raise(RuntimeError("boom"))})
    assert status == JobStatus.CANCELLED
    assert await _status(db_session, listing.id, "ingestion") == JobStatus.CANCELLED
    assert (await db_session.get(Listing, listing.id)).state == ListingState.UPLOADING


@pytest.mark.asyncio
async def test_retry_listing_with_no_jobs_enqueues_fresh_pipeline(db_session):
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Gate St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    n = await runner.retry_listing(db_session, listing, steps=STEPS)
    assert n == 3  # ingestion + packaging + content; the gate is created WAITING but not counted
    assert await _status(db_session, listing.id, "await_review") == JobStatus.WAITING
    assert (await db_session.get(Listing, listing.id)).state == ListingState.UPLOADING


@pytest.mark.asyncio
async def test_listing_progress_shape(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    await runner.run_job(factory, job.id, steps=STEPS, functions={"ingestion": lambda ctx: _ret({})})
    rows = await runner.listing_progress(db_session, listing.id, steps=STEPS)
    assert [r["name"] for r in rows] == ["ingestion", "packaging", "await_review", "content"]
    assert rows[0]["status"] == "completed" and rows[0]["completed_at"] is not None
    assert rows[1]["status"] == "pending" and rows[1]["error"] is None
    assert set(rows[0]) == {"name", "status", "completed_at", "progress", "error", "attempts"}


async def _ret(v):
    return v


async def _raise(exc):
    raise exc


@pytest.mark.asyncio
async def test_retry_listing_resets_running_jobs(db_session):
    """Retry is an explicit user action on a stuck listing: a RUNNING row whose
    worker vanished must be requeued too, not left for reclaim_stale."""
    listing, _ = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    assert job.step == "ingestion" and job.status == JobStatus.RUNNING
    n = await runner.retry_listing(db_session, listing, steps=STEPS)
    assert n == 1
    fresh = (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "ingestion"))).scalar_one()
    assert fresh.status == JobStatus.QUEUED
    assert fresh.locked_by is None and fresh.attempts == 0 and fresh.error is None


@pytest.mark.asyncio
async def test_retry_after_reject_reopens_the_review_gate(db_session):
    """Rejection cancels the live rows; retrying an analysed listing puts it
    back in front of the reviewer instead of leaving it FAILED."""
    listing, factory = await _setup(db_session)
    fns = {"ingestion": lambda ctx: _ret({}), "packaging": lambda ctx: _ret({"auto_approved": False})}
    for _ in range(2):
        job = await runner.claim_next(db_session, "w", steps=STEPS)
        await runner.run_job(factory, job.id, steps=STEPS, functions=fns)
    # Reject: cancel everything live, then fail the listing.
    assert await runner.cancel_listing_jobs(db_session, listing.id) == 2  # gate + content
    listing.state = ListingState.FAILED
    await db_session.flush()

    n = await runner.retry_listing(db_session, listing, steps=STEPS)
    assert n == 1  # content requeued; the gate is reopened but not counted
    assert await _status(db_session, listing.id, "await_review") == JobStatus.WAITING
    assert await _status(db_session, listing.id, "content") == JobStatus.QUEUED
    assert (await db_session.get(Listing, listing.id)).state == ListingState.AWAITING_REVIEW
