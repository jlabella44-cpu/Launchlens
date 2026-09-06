"""Job-table pipeline runner. See docs/superpowers/specs/2026-09-05-free-tier-rework-design.md (Phase 2)."""
from __future__ import annotations

import asyncio
import logging
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
        sibs = await _siblings(session, job.listing_id)
        results = {name: j.result for name, j in sibs.items() if j.status == JobStatus.DONE and j.result is not None}
        ctx = StepContext(listing_id=str(job.listing_id), tenant_id=str(job.tenant_id), results=results)
        fn = functions[job.step]
    try:
        result = await asyncio.wait_for(fn(ctx), timeout=step.timeout_s)
    except Exception as exc:  # noqa: BLE001 — every failure is classified in _handle_failure (Task 5)
        return await _handle_failure(session_factory, job_id, step, exc)
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
        job.status = JobStatus.DONE
        job.result = result if isinstance(result, dict) else {"result": result}
        job.error = None
        job.finished_at = _now()
        job.locked_by = None
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


async def _handle_failure(session_factory, job_id, step: Step, exc: BaseException) -> JobStatus:
    error = _describe(exc)
    logger.warning("pipeline.step.failed step=%s job=%s error=%s", step.name, job_id, error,
                   exc_info=not isinstance(exc, asyncio.TimeoutError))
    async with session_factory() as session:
        job = await session.get(PipelineJob, job_id)
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
