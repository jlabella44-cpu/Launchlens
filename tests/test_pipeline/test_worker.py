import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from sqlalchemy import select

from listingjet.config import Settings
from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import Step
from tests.test_agents.conftest import make_session_factory

STEPS = [Step("a"), Step("b", requires=("a",)), Step("c", requires=("a",))]


def make_concurrent_session_factory(session):
    """Like `make_session_factory`, but safe when the returned factory is called
    from more than one in-flight coroutine at once (as `worker_loop` does: its own
    tick loop and each spawned job task all call `session_factory()`).

    A real `AsyncSessionLocal`/`admin_session` opens an independent DB connection
    per call, so concurrent use is never a problem in production. This test shares
    a single real `AsyncSession` (one DB connection) for every "worker", which
    SQLAlchemy's `AsyncSession` does not allow two coroutines to touch at once
    (`InvalidRequestError: ... concurrent operations are not permitted`). A lock
    around each checkout serializes the brief moments any caller actually holds
    the session, without serializing the surrounding work (e.g. a step function's
    own sleep/IO, which never touches the session).
    """
    lock = asyncio.Lock()

    @asynccontextmanager
    async def _factory():
        async with lock:
            yield session

    return _factory


def test_worker_settings_defaults():
    f = Settings.model_fields
    assert f["worker_enabled"].default is True
    assert f["worker_concurrency"].default == 2
    assert f["worker_poll_interval_s"].default == 2.0


@pytest.mark.asyncio
async def test_worker_loop_drains_pipeline_with_bounded_concurrency(db_session):
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Loop St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)

    in_flight = 0
    peak = 0

    async def fn(ctx):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return {}

    stop = asyncio.Event()
    await runner.worker_loop(make_concurrent_session_factory(db_session), stop=stop, concurrency=1,
                             poll_interval_s=0.01, steps=STEPS,
                             functions={"a": fn, "b": fn, "c": fn}, max_ticks=20)
    statuses = {j.step: j.status for j in (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()}
    assert statuses == {"a": JobStatus.DONE, "b": JobStatus.DONE, "c": JobStatus.DONE}
    assert peak == 1
    assert runner.WORKER_STATE["last_tick"] is not None


@pytest.mark.asyncio
async def test_worker_loop_stops_on_event(db_session):
    stop = asyncio.Event()
    stop.set()
    await asyncio.wait_for(
        runner.worker_loop(make_session_factory(db_session), stop=stop, concurrency=1,
                           poll_interval_s=0.01, steps=STEPS, functions={}),
        timeout=2,
    )


@pytest.mark.asyncio
async def test_run_job_zombie_guard_ignores_reclaimed_and_reclaimed_job(db_session):
    """Reproduces the zombie-worker race end to end through the public run_job API.

    w1 claims job "a" (run_job's fn simulates a slow step by blocking on an event).
    While w1's fn is still "running", the job is reclaimed (locked_at pushed back,
    reclaim_stale requeues it) and w2 claims it fresh, giving it a new started_at.
    w1's fn then finishes and signals success. Because run_job captures started_at
    at its *first* read (job.started_at, taken before fn runs), and w2 has since
    changed it, w1's completion must be detected as stale via
    `job.started_at != started_at` (status is RUNNING again by then, so the old
    `status != RUNNING` guard alone would incorrectly accept it) and must not
    overwrite w2's ownership of the row.
    """
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Zombie St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)

    factory = make_session_factory(db_session)

    # w1 claims job "a".
    job = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert job.step == "a"
    job_id = job.id

    release_w1 = asyncio.Event()
    fn_started = asyncio.Event()

    async def slow_fn(ctx):
        # Signals that run_job's first session block (which captured started_at
        # and released the session) has already completed, then blocks until the
        # test has simulated the reclaim + re-claim by w2.
        fn_started.set()
        await release_w1.wait()
        return {}

    async def run_w1():
        return await runner.run_job(factory, job_id, steps=STEPS, functions={"a": slow_fn})

    w1_task = asyncio.create_task(run_w1())
    await fn_started.wait()  # run_job's first read (capturing started_at) has finished

    # Simulate w1's worker stalling long enough to be reclaimed.
    live_job = await db_session.get(PipelineJob, job_id)
    live_job.locked_at = live_job.locked_at - timedelta(hours=1)
    await db_session.flush()
    reclaimed = await runner.reclaim_stale(db_session, steps=STEPS)
    assert reclaimed == 1
    await db_session.commit()

    # w2 re-claims the now-QUEUED job, setting a new started_at.
    job2 = await runner.claim_next(db_session, "w2", steps=STEPS)
    assert job2.id == job_id

    release_w1.set()  # let w1's zombie run_job call finish
    status = await w1_task

    # w1's stale completion must not have overwritten w2's ownership.
    assert status == JobStatus.RUNNING
    fresh = await db_session.get(PipelineJob, job_id)
    await db_session.refresh(fresh)
    assert fresh.status == JobStatus.RUNNING
    assert fresh.locked_by == "w2"
    assert fresh.result is None


@pytest.mark.asyncio
async def test_worker_loop_runs_two_jobs_in_parallel(db_session):
    """concurrency=2 with three independent steps must actually overlap two."""
    par_steps = [Step("a"), Step("b"), Step("c")]
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "2 Loop St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[],
                                  steps=par_steps)

    in_flight = 0
    peak = 0
    both_running = asyncio.Event()

    async def fn(ctx):
        # Each step parks until a second step joins it (or 2s passes), so the
        # assertion below can't pass or fail on step-duration luck.
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        if in_flight >= 2:
            both_running.set()
        try:
            await asyncio.wait_for(both_running.wait(), timeout=2)
        except asyncio.TimeoutError:
            pass
        in_flight -= 1
        return {}

    stop = asyncio.Event()
    await runner.worker_loop(make_concurrent_session_factory(db_session), stop=stop, concurrency=2,
                             poll_interval_s=0.01, steps=par_steps,
                             functions={"a": fn, "b": fn, "c": fn}, max_ticks=30)
    statuses = {j.step: j.status for j in (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()}
    assert statuses == {"a": JobStatus.DONE, "b": JobStatus.DONE, "c": JobStatus.DONE}
    assert peak == 2


@pytest.mark.asyncio
async def test_requeue_owned_refunds_the_attempt(db_session):
    """Shutdown requeue must not permanently spend an attempt on work that
    never got to run to completion — only reclaim_stale (crash path) counts
    against max_attempts."""
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "4 Loop St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)

    job = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert job.step == "a"
    assert job.attempts == 1

    n = await runner.requeue_owned(db_session, "w1")
    await db_session.commit()
    assert n == 1

    refreshed = await db_session.get(PipelineJob, job.id)
    await db_session.refresh(refreshed)
    assert refreshed.status == JobStatus.QUEUED
    assert refreshed.locked_by is None
    assert refreshed.attempts == 0


@pytest.mark.asyncio
async def test_worker_loop_requeues_in_flight_jobs_on_shutdown(db_session):
    """A cancelled shutdown must not strand a job RUNNING until reclaim_stale
    notices it (which can be 2x the step timeout — up to 40 minutes)."""
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "3 Loop St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)

    running = asyncio.Event()

    async def slow(ctx):
        running.set()
        await asyncio.sleep(5)
        return {}

    stop = asyncio.Event()
    loop_task = asyncio.create_task(runner.worker_loop(
        make_concurrent_session_factory(db_session), stop=stop, concurrency=1,
        poll_interval_s=0.01, steps=STEPS, functions={"a": slow, "b": slow, "c": slow}))
    # The loop shares db_session with this test, so don't touch the session
    # until the loop has finished — wait on the step function instead.
    await asyncio.wait_for(running.wait(), timeout=10)

    stop.set()
    await asyncio.sleep(0.05)  # loop leaves its tick and starts draining
    loop_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(loop_task, timeout=10)

    job = (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "a"))).scalar_one()
    await db_session.refresh(job)
    assert job.status == JobStatus.QUEUED
    assert job.locked_by is None
