"""Queue-scale regression: many listings parked at the review gate must not
starve the queue.

`enqueue_pipeline` inserts every post-approval step as QUEUED up front, so each
listing sitting at `await_review` contributes ~12 rows that cannot run until a
human approves. The original `claim_next` locked the 50 oldest queued rows and
only then filtered dependencies, so a handful of in-review listings permanently
occupied the window and nothing was ever claimable.
"""
import uuid

import pytest
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner
from listingjet.pipeline.definition import PIPELINE, Step
from tests.test_agents.conftest import make_session_factory


async def _ok(ctx):
    return {}


async def _packaging(ctx):
    return {"auto_approved": False}


FUNCTIONS = {s.name: _ok for s in PIPELINE}
FUNCTIONS["packaging"] = _packaging


async def _listing(db_session, street: str) -> Listing:
    obj = Listing(tenant_id=uuid.uuid4(), address={"street": street}, metadata_={},
                  state=ListingState.UPLOADING)
    db_session.add(obj)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, obj, billing_model="legacy", enabled_addons=[])
    await db_session.commit()
    return obj


async def _status(db_session, listing_id, step):
    return (await db_session.execute(select(PipelineJob.status).where(
        PipelineJob.listing_id == listing_id, PipelineJob.step == step))).scalar_one()


@pytest.mark.asyncio
async def test_listings_parked_at_review_do_not_starve_the_queue(db_session):
    factory = make_session_factory(db_session)
    listings = [await _listing(db_session, f"{i} Scale St") for i in range(5)]

    # Drain everything that is runnable: every listing walks to its review gate.
    drained = 0
    while (job := await runner.claim_next(db_session, "w1")) is not None:
        await runner.run_job(factory, job.id, functions=FUNCTIONS)
        drained += 1
        assert drained < 200, "drain did not terminate"
    for listing in listings:
        assert await _status(db_session, listing.id, "packaging") == JobStatus.DONE
        assert await _status(db_session, listing.id, "await_review") == JobStatus.WAITING
        assert await _status(db_session, listing.id, "content") == JobStatus.QUEUED

    # 5 listings x ~12 unsatisfiable post-approval rows sit at the head of the
    # queue. A brand-new listing's ingestion is the ONLY runnable row and must
    # still be claimable.
    sixth = await _listing(db_session, "6 Scale St")
    job = await runner.claim_next(db_session, "w1")
    assert job is not None, "queue deadlocked behind listings parked at the review gate"
    assert (job.listing_id, job.step) == (sixth.id, "ingestion")

    # Approving the fourth listing releases its post-approval work, which is
    # older than the sixth listing's rows and so is claimed next.
    assert await runner.complete_review(db_session, listings[3].id) is True
    await db_session.commit()
    nxt = await runner.claim_next(db_session, "w1")
    assert nxt is not None
    assert (nxt.listing_id, nxt.step) == (listings[3].id, "content")
    assert nxt.status == JobStatus.RUNNING and nxt.locked_by == "w1"

    # The other three are still parked, untouched.
    for listing in listings[:3]:
        assert await _status(db_session, listing.id, "await_review") == JobStatus.WAITING


@pytest.mark.asyncio
async def test_two_workers_cannot_claim_the_same_job(db_session):
    """The compare-and-set claim means only one worker can win a given row."""
    steps = [Step("a"), Step("b", requires=("a",))]
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Race St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy",
                                  enabled_addons=[], steps=steps)
    await db_session.commit()

    first = await runner.claim_next(db_session, "w1", steps=steps)
    second = await runner.claim_next(db_session, "w2", steps=steps)
    assert first is not None and first.step == "a"
    assert second is None or second.id != first.id
    job = await db_session.get(PipelineJob, first.id)
    await db_session.refresh(job)
    assert job.locked_by == "w1" and job.attempts == 1
