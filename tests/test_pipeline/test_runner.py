import uuid

import pytest
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import Step
from tests.test_agents.conftest import make_session_factory

# A tiny pipeline for runner tests: a -> b -> gate -> c ; opt (optional) -> c ; skip (gated off)
STEPS = [
    Step("a"),
    Step("b", requires=("a",)),
    Step("opt", requires=("a",), optional=True, max_attempts=2),
    Step("skip", requires=("a",), gate="addon:never"),
    Step("gate", requires=("b",), gate="review"),
    Step("c", requires=("gate", "opt", "skip")),
]


async def _listing(db_session) -> Listing:
    obj = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Test St"}, metadata_={},
                  state=ListingState.UPLOADING)
    db_session.add(obj)
    await db_session.flush()
    return obj


async def _jobs(db_session, listing_id) -> dict[str, PipelineJob]:
    rows = (await db_session.execute(
        select(PipelineJob).where(PipelineJob.listing_id == listing_id))).scalars().all()
    return {j.step: j for j in rows}


@pytest.mark.asyncio
async def test_enqueue_creates_one_row_per_step_with_gates_applied(db_session):
    listing = await _listing(db_session)
    created = await runner.enqueue_pipeline(
        db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    assert len(created) == 6
    jobs = await _jobs(db_session, listing.id)
    assert jobs["a"].status == JobStatus.QUEUED
    assert jobs["gate"].status == JobStatus.WAITING
    assert jobs["skip"].status == JobStatus.SKIPPED
    assert jobs["opt"].max_attempts == 2
    # idempotent
    again = await runner.enqueue_pipeline(
        db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    assert {j.id for j in again} == {j.id for j in created}


@pytest.mark.asyncio
async def test_enqueue_raises_on_unknown_gate(db_session):
    listing = await _listing(db_session)
    bad_steps = [Step("a"), Step("z", requires=("a",), gate="bogus")]
    with pytest.raises(ValueError, match="unknown gate"):
        await runner.enqueue_pipeline(
            db_session, listing, billing_model="legacy", enabled_addons=[], steps=bad_steps)


@pytest.mark.asyncio
async def test_claim_respects_dependencies_and_marks_running(db_session):
    listing = await _listing(db_session)
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    job = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert job is not None and job.step == "a"
    assert job.status == JobStatus.RUNNING and job.locked_by == "w1" and job.locked_at is not None
    # b/opt are blocked on a, which is running, so nothing else is claimable
    assert await runner.claim_next(db_session, "w2", steps=STEPS) is None


@pytest.mark.asyncio
async def test_run_job_success_stores_result_and_unblocks_dependents(db_session):
    listing = await _listing(db_session)
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=STEPS)
    calls: list[str] = []

    async def fn_a(ctx):
        calls.append("a")
        return {"n": 1}

    async def fn_b(ctx):
        calls.append("b")
        assert ctx.results["a"] == {"n": 1}
        return {"n": 2}

    functions = {"a": fn_a, "b": fn_b, "opt": fn_a, "c": fn_a}
    factory = make_session_factory(db_session)

    job = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert await runner.run_job(factory, job.id, steps=STEPS, functions=functions) == JobStatus.DONE
    jobs = await _jobs(db_session, listing.id)
    assert jobs["a"].status == JobStatus.DONE and jobs["a"].result == {"n": 1}
    assert jobs["a"].finished_at is not None

    nxt = await runner.claim_next(db_session, "w1", steps=STEPS)
    assert nxt.step in ("b", "opt")
    await runner.run_job(factory, nxt.id, steps=STEPS, functions=functions)
    assert calls[:2] == ["a", nxt.step]


def test_is_satisfied_rules():
    step = Step("x", optional=True)
    req = Step("y")
    assert runner.is_satisfied(None, req) is False
    for status, expected in [(JobStatus.DONE, True), (JobStatus.SKIPPED, True),
                             (JobStatus.QUEUED, False), (JobStatus.RUNNING, False)]:
        assert runner.is_satisfied(PipelineJob(step="y", status=status), req) is expected
    assert runner.is_satisfied(PipelineJob(step="x", status=JobStatus.FAILED), step) is True
    assert runner.is_satisfied(PipelineJob(step="y", status=JobStatus.FAILED), req) is False


@pytest.mark.asyncio
async def test_feature_gate_skips_step_when_flag_off(db_session):
    from unittest.mock import patch

    from listingjet import features
    listing = await _listing(db_session)
    steps = [Step("a"), Step("m", requires=("a",), optional=True, gate="feature:microsite")]
    with patch.object(features.settings, "features", ""):
        await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[], steps=steps)
    jobs = await _jobs(db_session, listing.id)
    assert jobs["m"].status == JobStatus.SKIPPED
