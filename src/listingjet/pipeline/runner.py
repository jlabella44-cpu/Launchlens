"""Job-table pipeline runner. See docs/superpowers/specs/2026-09-05-free-tier-rework-design.md (Phase 2)."""
from __future__ import annotations

import asyncio
import logging
import socket
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline.definition import PIPELINE, Step
from listingjet.pipeline.steps import STEP_FUNCTIONS, StepContext

logger = logging.getLogger(__name__)

_NON_RETRYABLE = (ValueError, KeyError, TypeError, PermissionError, NotImplementedError)

SATISFIED = {JobStatus.DONE, JobStatus.SKIPPED}

WORKER_STATE: dict = {"last_tick": None, "worker_id": None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gated_off(step: Step, billing_model: str, enabled_addons: list[str]) -> bool:
    if step.gate is None or step.gate == "review":
        return False
    if step.gate.startswith("addon:"):
        return step.gate.removeprefix("addon:") not in enabled_addons
    if step.gate == "video":
        return billing_model == "credit" and "ai_video_tour" not in enabled_addons
    raise ValueError(f"unknown gate {step.gate!r} on step {step.name}")


async def enqueue_pipeline(
    session: AsyncSession,
    listing: Listing,
    *,
    billing_model: str,
    enabled_addons: list[str],
    steps: list[Step] = PIPELINE,
) -> list[PipelineJob]:
    existing = {
        j.step: j for j in (await session.execute(
            select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalars().all()
    }
    jobs: list[PipelineJob] = []
    for step in steps:
        if step.name in existing:
            jobs.append(existing[step.name])
            continue
        if step.gate == "review":
            status = JobStatus.WAITING
        elif _gated_off(step, billing_model, enabled_addons):
            status = JobStatus.SKIPPED
        else:
            status = JobStatus.QUEUED
        job = PipelineJob(
            tenant_id=listing.tenant_id, listing_id=listing.id, step=step.name,
            status=status, max_attempts=step.max_attempts, run_after=_now(),
            payload={"billing_model": billing_model, "enabled_addons": enabled_addons},
        )
        session.add(job)
        jobs.append(job)
    await session.flush()
    return jobs


def is_satisfied(dep_job: PipelineJob | None, dep_step: Step) -> bool:
    if dep_job is None:
        return False
    if dep_job.status in SATISFIED:
        return True
    return dep_job.status == JobStatus.FAILED and dep_step.optional


async def _siblings(session: AsyncSession, listing_id) -> dict[str, PipelineJob]:
    rows = (await session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing_id))).scalars().all()
    return {j.step: j for j in rows}


async def claim_next(session: AsyncSession, worker_id: str, *, steps: list[Step] = PIPELINE) -> PipelineJob | None:
    """Claim the oldest runnable job. Marks it RUNNING and commits before returning."""
    index = {s.name: s for s in steps}
    try:
        candidates = (await session.execute(
            select(PipelineJob)
            .where(PipelineJob.status == JobStatus.QUEUED, PipelineJob.run_after <= _now())
            .order_by(PipelineJob.run_after, PipelineJob.created_at)
            .limit(50)
            .with_for_update(skip_locked=True)
        )).scalars().all()
    except Exception:
        # FOR UPDATE SKIP LOCKED may fail inside a savepoint (e.g. tests);
        # fall back but still lock rows to prevent duplicate delivery.
        candidates = (await session.execute(
            select(PipelineJob)
            .where(PipelineJob.status == JobStatus.QUEUED, PipelineJob.run_after <= _now())
            .order_by(PipelineJob.run_after, PipelineJob.created_at)
            .limit(50)
            .with_for_update()
        )).scalars().all()
    sibling_cache: dict = {}
    for job in candidates:
        step = index.get(job.step)
        if step is None:
            continue
        if job.listing_id not in sibling_cache:
            sibling_cache[job.listing_id] = await _siblings(session, job.listing_id)
        sibs = sibling_cache[job.listing_id]
        if all(is_satisfied(sibs.get(dep), index[dep]) for dep in step.requires):
            job.status = JobStatus.RUNNING
            job.locked_by = worker_id
            job.locked_at = _now()
            job.started_at = _now()
            job.attempts += 1
            await session.commit()
            return job
    await session.commit()  # release the row locks
    return None


async def run_job(session_factory, job_id, *, steps: list[Step] = PIPELINE, functions=STEP_FUNCTIONS) -> JobStatus:
    index = {s.name: s for s in steps}
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
        step = index[job.step]
        started_at = job.started_at
        sibs = await _siblings(session, job.listing_id)
        results = {name: j.result for name, j in sibs.items() if j.status == JobStatus.DONE and j.result is not None}
        ctx = StepContext(listing_id=str(job.listing_id), tenant_id=str(job.tenant_id), results=results)
        fn = functions[job.step]
    try:
        result = await asyncio.wait_for(fn(ctx), timeout=step.timeout_s)
    except Exception as exc:  # noqa: BLE001 — every failure is classified in _handle_failure (Task 5)
        return await _handle_failure(session_factory, job_id, step, exc, started_at=started_at)
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
        # A job reclaimed by reclaim_stale and re-claimed by another worker is RUNNING
        # again with a *new* started_at — the status check alone can't tell this zombie
        # completion apart from the real owner, so also require started_at to match.
        if job.status != JobStatus.RUNNING or job.started_at != started_at:
            logger.warning("pipeline.step.stale_completion step=%s job=%s status=%s",
                           job.step, job_id, job.status)
            return job.status
        job.status = JobStatus.DONE
        job.result = result if isinstance(result, dict) else {"result": result}
        job.error = None
        job.finished_at = _now()
        job.locked_by = None
        if job.step == "packaging" and isinstance(job.result, dict) and job.result.get("auto_approved") is True:
            await complete_review(session, job.listing_id)
        await session.commit()
    logger.info("pipeline.step.done listing=%s step=%s", job.listing_id, job.step)
    return JobStatus.DONE


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, asyncio.TimeoutError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    try:
        import anthropic
        if isinstance(exc, anthropic.BadRequestError):
            return False
        if isinstance(exc, (anthropic.RateLimitError, anthropic.APIConnectionError)):
            return True
    except ImportError:
        pass
    if isinstance(exc, _NON_RETRYABLE):
        return False
    return True


def backoff_seconds(attempt: int) -> int:
    return min(600, 30 * (2 ** (attempt - 1)))


def _describe(exc: BaseException) -> str:
    if isinstance(exc, asyncio.TimeoutError):
        return "step timed out"
    return f"{type(exc).__name__}: {exc}"[:2000]


async def fail_listing(session: AsyncSession, listing_id, *, step: str, error: str) -> None:
    from listingjet.services.events import emit_event

    listing = await session.get(Listing, listing_id)
    if listing is None:
        return
    listing.state = ListingState.FAILED
    await session.execute(
        update(PipelineJob)
        .where(PipelineJob.listing_id == listing_id,
               PipelineJob.status.in_([JobStatus.QUEUED, JobStatus.WAITING]))
        .values(status=JobStatus.CANCELLED)
    )
    await emit_event(session=session, event_type="pipeline.failed",
                     payload={"step": step, "error": error},
                     tenant_id=str(listing.tenant_id), listing_id=str(listing_id))


async def _handle_failure(session_factory, job_id, step: Step, exc: BaseException, *,
                          started_at: datetime | None = None) -> JobStatus:
    error = _describe(exc)
    logger.warning("pipeline.step.failed step=%s job=%s error=%s", step.name, job_id, error,
                   exc_info=not isinstance(exc, asyncio.TimeoutError))
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
        if job.status != JobStatus.RUNNING or (started_at is not None and job.started_at != started_at):
            logger.warning("pipeline.step.stale_completion step=%s job=%s status=%s",
                           step.name, job_id, job.status)
            return job.status
        job.error = error
        job.locked_by = None
        if is_retryable(exc) and job.attempts < job.max_attempts:
            job.status = JobStatus.QUEUED
            job.run_after = _now() + timedelta(seconds=backoff_seconds(job.attempts))
            await session.commit()
            return JobStatus.QUEUED
        job.status = JobStatus.FAILED
        job.finished_at = _now()
        if not step.optional:
            await fail_listing(session, job.listing_id, step=step.name, error=error)
        await session.commit()
        return JobStatus.FAILED


async def reclaim_stale(session: AsyncSession, *, steps: list[Step] = PIPELINE) -> int:
    index = {s.name: s for s in steps}
    rows = (await session.execute(
        select(PipelineJob).where(PipelineJob.status == JobStatus.RUNNING).with_for_update(skip_locked=True)
    )).scalars().all()
    reclaimed = 0
    now = _now()
    for job in rows:
        step = index.get(job.step)
        limit = timedelta(seconds=2 * (step.timeout_s if step else 600))
        if job.locked_at and job.locked_at < now - limit:
            job.status = JobStatus.QUEUED
            job.locked_by = None
            job.error = "reclaimed after worker died"
            reclaimed += 1
    await session.flush()
    return reclaimed


_STATUS_LABEL = {
    JobStatus.QUEUED: "pending", JobStatus.WAITING: "pending", JobStatus.RUNNING: "in_progress",
    JobStatus.DONE: "completed", JobStatus.FAILED: "failed",
    JobStatus.SKIPPED: "skipped", JobStatus.CANCELLED: "skipped",
}


async def complete_review(session: AsyncSession, listing_id) -> bool:
    res = await session.execute(
        update(PipelineJob)
        .where(PipelineJob.listing_id == listing_id, PipelineJob.step == "await_review",
               PipelineJob.status == JobStatus.WAITING)
        .values(status=JobStatus.DONE, finished_at=_now(), result={"approved": True})
    )
    await session.flush()
    return res.rowcount == 1


async def retry_listing(session: AsyncSession, listing: Listing, *, steps: list[Step] = PIPELINE,
                        billing_model: str = "legacy", enabled_addons: list[str] | None = None) -> int:
    index = {s.name: s for s in steps}
    sibs = await _siblings(session, listing.id)
    if not sibs:
        created = await enqueue_pipeline(session, listing, billing_model=billing_model,
                                         enabled_addons=enabled_addons or [], steps=steps)
        listing.state = ListingState.UPLOADING
        # Review-gate steps are created (as WAITING) but not counted, matching the existing-jobs branch below.
        return sum(1 for j in created if index.get(j.step) is None or index[j.step].gate != "review")
    n = 0
    for job in sibs.values():
        if job.status in (JobStatus.FAILED, JobStatus.CANCELLED):
            step = index.get(job.step)
            is_gate = step is not None and step.gate == "review"
            # The gate is reset to WAITING (reopened) but not counted, since it isn't a requeued work item.
            job.status = JobStatus.WAITING if is_gate else JobStatus.QUEUED
            job.attempts = 0
            job.error = None
            job.locked_by = None
            job.run_after = _now()
            if not is_gate:
                n += 1
    def _done(name: str) -> bool:
        j = sibs.get(name)
        return j is not None and j.status in SATISFIED
    if not _done("ingestion"):
        listing.state = ListingState.UPLOADING
    elif not _done("packaging"):
        listing.state = ListingState.ANALYZING
    await session.flush()
    return n


async def cancel_listing_jobs(session: AsyncSession, listing_id) -> int:
    res = await session.execute(
        update(PipelineJob)
        .where(PipelineJob.listing_id == listing_id,
               PipelineJob.status.in_([JobStatus.QUEUED, JobStatus.WAITING, JobStatus.RUNNING]))
        .values(status=JobStatus.CANCELLED, locked_by=None)
    )
    await session.flush()
    return res.rowcount


async def listing_progress(session: AsyncSession, listing_id, *, steps: list[Step] = PIPELINE) -> list[dict]:
    sibs = await _siblings(session, listing_id)
    rows = []
    for step in steps:
        j = sibs.get(step.name)
        if j is None:
            continue
        rows.append({
            "name": step.name,
            "status": _STATUS_LABEL[j.status],
            "completed_at": j.finished_at.isoformat() if j.finished_at and j.status == JobStatus.DONE else None,
            "progress": None,
            "error": j.error if j.status == JobStatus.FAILED else None,
            "attempts": j.attempts,
        })
    return rows


async def worker_loop(session_factory, *, stop: asyncio.Event, concurrency: int, poll_interval_s: float,
                      steps: list[Step] = PIPELINE, functions=STEP_FUNCTIONS,
                      max_ticks: int | None = None) -> None:
    """Drain claimable pipeline jobs with bounded concurrency until `stop` is set.

    Each tick: reclaim jobs abandoned by dead workers, then claim up to
    `concurrency` jobs and run each in its own task. Sleeps `poll_interval_s`
    when a tick claims nothing so idle workers don't hammer the DB.
    """
    worker_id = f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"
    WORKER_STATE["worker_id"] = worker_id
    tasks: set[asyncio.Task] = set()
    free_slots = concurrency
    ticks = 0

    async def _run(job_id):
        nonlocal free_slots
        try:
            await run_job(session_factory, job_id, steps=steps, functions=functions)
        except Exception:  # noqa: BLE001 — never let one job crash the loop
            logger.exception("pipeline.run_job crashed job=%s", job_id)
        finally:
            free_slots += 1

    while not stop.is_set():
        ticks += 1
        WORKER_STATE["last_tick"] = _now()
        claimed = 0
        try:
            async with session_factory() as session:
                await reclaim_stale(session, steps=steps)
                await session.commit()
            while free_slots > 0 and not stop.is_set():
                async with session_factory() as session:
                    job = await claim_next(session, worker_id, steps=steps)
                if job is None:
                    break
                claimed += 1
                free_slots -= 1
                t = asyncio.create_task(_run(job.id))
                tasks.add(t)
                t.add_done_callback(tasks.discard)
                await asyncio.sleep(0)  # let the task start
        except Exception:  # noqa: BLE001
            logger.exception("pipeline.worker_loop tick failed")
        if max_ticks is not None and ticks >= max_ticks:
            break
        if claimed == 0:
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_interval_s)
            except asyncio.TimeoutError:
                pass
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def periodic_loop(session_factory, *, stop: asyncio.Event) -> None:
    """Runs demo cleanup hourly and baseline aggregation weekly, in-process.

    `session_factory` is accepted for interface symmetry with `worker_loop`
    (and so a future task can pass it through); the periodic tasks currently
    open their own admin sessions internally. Each task's last-run time is
    kept in memory only — a restart simply re-runs it, which is harmless.
    """
    from listingjet.pipeline.periodic import run_baseline_aggregation, run_demo_cleanup

    schedule = [("demo_cleanup", run_demo_cleanup, timedelta(hours=1)),
                ("baseline_aggregation", run_baseline_aggregation, timedelta(days=7))]
    last: dict[str, datetime] = {}
    while not stop.is_set():
        for name, fn, every in schedule:
            if name not in last or _now() - last[name] >= every:
                try:
                    await fn()
                except Exception:  # noqa: BLE001
                    logger.exception("periodic task failed name=%s", name)
                last[name] = _now()
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass
