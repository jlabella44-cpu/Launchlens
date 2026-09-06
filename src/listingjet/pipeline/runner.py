"""Job-table pipeline runner. See docs/superpowers/specs/2026-09-05-free-tier-rework-design.md (Phase 2)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline.definition import PIPELINE, Step
from listingjet.pipeline.steps import STEP_FUNCTIONS, StepContext

logger = logging.getLogger(__name__)

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


async def _handle_failure(session_factory, job_id, step: Step, exc: BaseException) -> JobStatus:
    raise NotImplementedError  # Task 5
