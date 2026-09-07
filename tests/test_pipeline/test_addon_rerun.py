"""Add-on bought after enqueue (or after delivery) must re-run its gated
step plus everything downstream of it. See `runner.enqueue_addon_steps`."""
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import runner

# Everything from `ingestion` through `distribution`, excluding the two
# addon-gated steps (which stay SKIPPED — `enabled_addons=[]`) and the
# phase-3 best-effort steps after distribution (which stay QUEUED — they
# haven't run yet, so they mustn't look "satisfied" and get swept up too).
_DONE_THROUGH_DISTRIBUTION = [
    "ingestion", "photo_analysis", "property_verification", "coverage",
    "floorplan", "dollhouse_render", "packaging", "video_baseline",
    "await_review", "content_social", "brand", "social_cuts", "mls_export",
    "distribution",
]


async def _setup_delivered_listing(db_session) -> Listing:
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Addon Rerun Ln"},
                      metadata_={}, state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    await runner.enqueue_pipeline(db_session, listing, billing_model="legacy", enabled_addons=[])

    sibs = await runner._siblings(db_session, listing.id)
    for name in _DONE_THROUGH_DISTRIBUTION:
        job = sibs[name]
        job.status = JobStatus.DONE
        job.result = {}
    listing.state = ListingState.DELIVERED
    await db_session.flush()
    return listing


async def _status(db_session, listing_id, step):
    return (await db_session.execute(select(PipelineJob.status).where(
        PipelineJob.listing_id == listing_id, PipelineJob.step == step))).scalar_one()


@pytest.mark.asyncio
async def test_enqueue_addon_steps_reruns_gated_step_and_dependents(db_session):
    listing = await _setup_delivered_listing(db_session)

    n = await runner.enqueue_addon_steps(db_session, listing, "ai_video_tour")

    assert n == 3
    assert await _status(db_session, listing.id, "video_ai") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "social_cuts") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "distribution") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "video_baseline") == JobStatus.DONE  # untouched
    assert (await db_session.get(Listing, listing.id)).state == ListingState.EXPORTING


@pytest.mark.asyncio
async def test_enqueue_addon_steps_is_idempotent(db_session):
    listing = await _setup_delivered_listing(db_session)
    await runner.enqueue_addon_steps(db_session, listing, "ai_video_tour")

    n = await runner.enqueue_addon_steps(db_session, listing, "ai_video_tour")

    assert n == 0


@pytest.mark.asyncio
async def test_enqueue_addon_steps_resets_attempts_and_error(db_session):
    listing = await _setup_delivered_listing(db_session)
    sibs = await runner._siblings(db_session, listing.id)
    sibs["video_ai"].status = JobStatus.FAILED
    sibs["video_ai"].attempts = 3
    sibs["video_ai"].error = "boom"
    await db_session.flush()

    n = await runner.enqueue_addon_steps(db_session, listing, "ai_video_tour")

    assert n == 3
    job = (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "video_ai"))).scalar_one()
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 0
    assert job.error is None


@pytest.mark.asyncio
async def test_enqueue_addon_steps_for_unknown_slug_is_noop(db_session):
    listing = await _setup_delivered_listing(db_session)

    n = await runner.enqueue_addon_steps(db_session, listing, "not_a_real_addon")

    assert n == 0
    assert (await db_session.get(Listing, listing.id)).state == ListingState.DELIVERED


@pytest.mark.asyncio
async def test_enqueue_addon_steps_never_resets_the_review_gate(db_session):
    """Regression: `virtual_staging` gates `floorplan`, which `await_review`
    transitively requires — so `await_review` is technically an "ancestor" of
    the gated step. It must never be reset: it has no worker function
    (`await_review` is completed only by the review API, never claimed), so
    resetting it to QUEUED would strand it forever; resetting it to WAITING
    would reopen a gate on an already-delivered listing. Only steps strictly
    *downstream* of `virtual_staging` get reset, and video_ai (a different,
    unpurchased add-on) is untouched."""
    listing = await _setup_delivered_listing(db_session)

    n = await runner.enqueue_addon_steps(db_session, listing, "virtual_staging")

    assert n > 0
    assert await _status(db_session, listing.id, "virtual_staging") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "await_review") == JobStatus.DONE  # untouched
    assert await _status(db_session, listing.id, "video_ai") == JobStatus.SKIPPED  # untouched
    # Downstream of virtual_staging (via floorplan) and DONE — reset.
    assert await _status(db_session, listing.id, "floorplan") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "packaging") == JobStatus.QUEUED
    assert await _status(db_session, listing.id, "distribution") == JobStatus.QUEUED
    # Upstream-only sibling of virtual_staging — never touched.
    assert await _status(db_session, listing.id, "property_verification") == JobStatus.DONE
    assert (await db_session.get(Listing, listing.id)).state == ListingState.EXPORTING


@pytest.mark.asyncio
async def test_enqueue_addon_steps_leaves_feature_gated_steps_skipped(db_session):
    """A SKIPPED dependent must be re-checked against its OWN gate, not
    blindly un-skipped just because it's downstream of the purchased add-on:
    a feature-gated step stays SKIPPED regardless of which add-on was
    bought."""
    with patch("listingjet.features.enabled_set", return_value=set()):
        listing = await _setup_delivered_listing(db_session)
        sibs = await runner._siblings(db_session, listing.id)
        assert sibs["microsite"].status == JobStatus.SKIPPED  # feature off at enqueue time
        assert sibs["learning"].status == JobStatus.SKIPPED

        n = await runner.enqueue_addon_steps(db_session, listing, "ai_video_tour")

        assert n == 3  # video_ai, social_cuts, distribution — same as the base case
        assert await _status(db_session, listing.id, "microsite") == JobStatus.SKIPPED
        assert await _status(db_session, listing.id, "learning") == JobStatus.SKIPPED


@pytest.mark.asyncio
async def test_enqueue_addon_steps_already_active_addon_touches_nothing(db_session):
    """Re-"purchasing" an add-on whose gated step is already QUEUED (active,
    not SKIPPED/FAILED/CANCELLED) must not reset any of its dependents either
    — there's nothing new to re-run."""
    listing = await _setup_delivered_listing(db_session)
    await runner.enqueue_addon_steps(db_session, listing, "ai_video_tour")
    social_cuts_before = (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "social_cuts"))).scalar_one()
    run_after_before = social_cuts_before.run_after

    n = await runner.enqueue_addon_steps(db_session, listing, "ai_video_tour")

    assert n == 0
    social_cuts_after = (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "social_cuts"))).scalar_one()
    assert social_cuts_after.run_after == run_after_before  # untouched, not just "still QUEUED"
