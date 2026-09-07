import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from listingjet.models.event import Event
from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import Step
from tests.test_agents.conftest import make_session_factory

STEPS = [Step("a", max_attempts=2, timeout_s=1), Step("opt", requires=("a",), optional=True, max_attempts=1),
         Step("b", requires=("a",)), Step("c", requires=("b", "opt"))]


async def _setup(db_session):
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Fail St"}, metadata_={},
                      state=ListingState.ANALYZING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    return listing, make_session_factory(db_session)


async def _job(db_session, listing_id, step):
    return (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing_id, PipelineJob.step == step))).scalar_one()


def test_is_retryable_classification():
    assert runner.is_retryable(asyncio.TimeoutError()) is True
    assert runner.is_retryable(ConnectionError()) is True
    req = httpx.Request("GET", "http://x")
    assert runner.is_retryable(httpx.HTTPStatusError("x", request=req, response=httpx.Response(503, request=req))) is True
    assert runner.is_retryable(httpx.HTTPStatusError("x", request=req, response=httpx.Response(429, request=req))) is True
    assert runner.is_retryable(httpx.HTTPStatusError("x", request=req, response=httpx.Response(400, request=req))) is False
    assert runner.is_retryable(ValueError("Listing not found")) is False
    assert runner.is_retryable(RuntimeError("boom")) is True


def test_backoff_grows_and_caps():
    assert [runner.backoff_seconds(n) for n in (1, 2, 3, 6)] == [30, 60, 120, 600]


@pytest.mark.asyncio
async def test_retryable_failure_requeues_with_backoff(db_session):
    listing, factory = await _setup(db_session)

    async def boom(ctx):
        raise RuntimeError("transient")

    job = await runner.claim_next(db_session, "w", steps=STEPS)
    status = await runner.run_job(factory, job.id, steps=STEPS, functions={"a": boom})
    assert status == JobStatus.QUEUED
    j = await _job(db_session, listing.id, "a")
    assert j.attempts == 1 and "transient" in j.error
    assert j.run_after > datetime.now(timezone.utc) + timedelta(seconds=20)
    assert (await db_session.get(Listing, listing.id)).state == ListingState.ANALYZING


@pytest.mark.asyncio
async def test_non_retryable_failure_fails_listing_and_cancels_rest(db_session):
    listing, factory = await _setup(db_session)

    async def bad(ctx):
        raise ValueError("Listing not found")

    job = await runner.claim_next(db_session, "w", steps=STEPS)
    status = await runner.run_job(factory, job.id, steps=STEPS, functions={"a": bad})
    assert status == JobStatus.FAILED
    jobs = {j.step: j for j in (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()}
    assert jobs["a"].status == JobStatus.FAILED and jobs["a"].attempts == 1
    assert {jobs[s].status for s in ("opt", "b", "c")} == {JobStatus.CANCELLED}
    assert (await db_session.get(Listing, listing.id)).state == ListingState.FAILED
    evt = (await db_session.execute(select(Event).where(
        Event.listing_id == listing.id, Event.event_type == "pipeline.failed"))).scalar_one()
    assert evt.payload["step"] == "a" and "Listing not found" in evt.payload["error"]


@pytest.mark.asyncio
async def test_optional_failure_does_not_fail_listing(db_session):
    listing, factory = await _setup(db_session)

    async def ok(ctx):
        return {}

    async def bad(ctx):
        raise ValueError("no")

    fns = {"a": ok, "opt": bad, "b": ok, "c": ok}
    for _ in range(2):  # a, then opt (or b)
        job = await runner.claim_next(db_session, "w", steps=STEPS)
        await runner.run_job(factory, job.id, steps=STEPS, functions=fns)
    # drain remaining
    while (job := await runner.claim_next(db_session, "w", steps=STEPS)) is not None:
        await runner.run_job(factory, job.id, steps=STEPS, functions=fns)
    jobs = {j.step: j for j in (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()}
    assert jobs["opt"].status == JobStatus.FAILED
    assert jobs["c"].status == JobStatus.DONE
    assert (await db_session.get(Listing, listing.id)).state == ListingState.ANALYZING


@pytest.mark.asyncio
async def test_timeout_is_retryable(db_session):
    listing, factory = await _setup(db_session)

    async def slow(ctx):
        await asyncio.sleep(5)

    job = await runner.claim_next(db_session, "w", steps=STEPS)
    assert await runner.run_job(factory, job.id, steps=STEPS, functions={"a": slow}) == JobStatus.QUEUED
    assert "timed out" in (await _job(db_session, listing.id, "a")).error


@pytest.mark.asyncio
async def test_reclaim_stale_running_jobs(db_session):
    listing, factory = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    job.locked_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.flush()
    assert await runner.reclaim_stale(db_session, steps=STEPS) == 1
    j = await _job(db_session, listing.id, "a")
    assert j.status == JobStatus.QUEUED and j.locked_by is None


@pytest.mark.asyncio
async def test_reclaim_stale_fails_job_that_is_out_of_attempts(db_session):
    """A job whose worker died on its last attempt must not go back to the
    queue forever — it fails, and (being non-optional) fails the listing."""
    listing, _ = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)
    job.attempts = job.max_attempts  # "a" is max_attempts=2
    job.error = "earlier boom"
    job.locked_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.flush()

    assert await runner.reclaim_stale(db_session, steps=STEPS) == 1
    j = await _job(db_session, listing.id, "a")
    assert j.status == JobStatus.FAILED
    assert j.locked_by is None and j.finished_at is not None
    assert "max attempts reached" in j.error and "earlier boom" in j.error
    assert (await db_session.get(Listing, listing.id)).state == ListingState.FAILED
    assert (await _job(db_session, listing.id, "b")).status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_reclaim_stale_optional_step_out_of_attempts_spares_the_listing(db_session):
    listing, _ = await _setup(db_session)
    j = await _job(db_session, listing.id, "opt")  # optional, max_attempts=1
    j.status = JobStatus.RUNNING
    j.attempts = 1
    j.locked_by = "dead-worker"
    j.locked_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.flush()

    assert await runner.reclaim_stale(db_session, steps=STEPS) == 1
    j = await _job(db_session, listing.id, "opt")
    assert j.status == JobStatus.FAILED and "max attempts reached" in j.error
    assert (await db_session.get(Listing, listing.id)).state == ListingState.ANALYZING


@pytest.mark.asyncio
async def test_reclaim_stale_requeues_and_appends_to_the_existing_error(db_session):
    listing, _ = await _setup(db_session)
    job = await runner.claim_next(db_session, "w", steps=STEPS)  # attempts=1 < 2
    job.error = "earlier boom"
    job.locked_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.flush()

    assert await runner.reclaim_stale(db_session, steps=STEPS) == 1
    j = await _job(db_session, listing.id, "a")
    assert j.status == JobStatus.QUEUED and j.locked_by is None
    assert j.error == "earlier boom\nreclaimed after worker died"


@pytest.mark.asyncio
async def test_reclaim_stale_respects_each_step_timeout(db_session):
    """SQL narrows on the smallest step timeout (2 x 1s here); Python still
    applies each job's own limit, so "b" (600s) is left alone."""
    listing, _ = await _setup(db_session)
    j = await _job(db_session, listing.id, "b")
    j.status = JobStatus.RUNNING
    j.attempts = 1
    j.locked_by = "w"
    j.locked_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    await db_session.flush()
    assert await runner.reclaim_stale(db_session, steps=STEPS) == 0
    assert (await _job(db_session, listing.id, "b")).status == JobStatus.RUNNING
