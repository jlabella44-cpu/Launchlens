"""`periodic.fail_stuck_listings` — the stuck-listing watchdog. See
`pipeline.runner.periodic_loop`, which schedules it hourly."""
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob
from listingjet.pipeline import periodic, runner
from tests.test_agents.conftest import make_session_factory

MAX_AGE_HOURS = 6
_STALE = timedelta(hours=MAX_AGE_HOURS + 1)
_FRESH = timedelta(minutes=5)


async def _make_listing(db_session, *, state: ListingState) -> Listing:
    listing = Listing(tenant_id=uuid.uuid4(), address={"street": "1 Stuck St"},
                      metadata_={}, state=state)
    db_session.add(listing)
    await db_session.flush()
    return listing


async def _add_job(db_session, listing, *, step: str, status: JobStatus, age: timedelta) -> None:
    job = PipelineJob(
        tenant_id=listing.tenant_id, listing_id=listing.id, step=step,
        status=status, run_after=runner._now(),
    )
    db_session.add(job)
    await db_session.flush()
    # updated_at has onupdate=func.now(); an explicit value in .values()
    # overrides that, so this is the only way to backdate it.
    await db_session.execute(
        update(PipelineJob).where(PipelineJob.id == job.id)
        .values(updated_at=runner._now() - age)
    )
    await db_session.flush()


@pytest.mark.asyncio
async def test_fail_stuck_listings_times_out_a_silently_stuck_listing(db_session):
    listing = await _make_listing(db_session, state=ListingState.ANALYZING)
    await _add_job(db_session, listing, step="ingestion", status=JobStatus.DONE, age=_STALE)
    await _add_job(db_session, listing, step="photo_analysis", status=JobStatus.QUEUED, age=_STALE)

    n = await periodic.fail_stuck_listings(make_session_factory(db_session), max_age_hours=MAX_AGE_HOURS)

    assert n == 1
    refreshed = await db_session.get(Listing, listing.id)
    assert refreshed.state == ListingState.PIPELINE_TIMEOUT


@pytest.mark.asyncio
async def test_fail_stuck_listings_ignores_listing_with_running_job(db_session):
    listing = await _make_listing(db_session, state=ListingState.ANALYZING)
    await _add_job(db_session, listing, step="ingestion", status=JobStatus.DONE, age=_STALE)
    await _add_job(db_session, listing, step="photo_analysis", status=JobStatus.RUNNING, age=_STALE)

    n = await periodic.fail_stuck_listings(make_session_factory(db_session), max_age_hours=MAX_AGE_HOURS)

    assert n == 0
    refreshed = await db_session.get(Listing, listing.id)
    assert refreshed.state == ListingState.ANALYZING


@pytest.mark.asyncio
async def test_fail_stuck_listings_ignores_delivered_listing(db_session):
    listing = await _make_listing(db_session, state=ListingState.DELIVERED)
    await _add_job(db_session, listing, step="distribution", status=JobStatus.DONE, age=_STALE)

    n = await periodic.fail_stuck_listings(make_session_factory(db_session), max_age_hours=MAX_AGE_HOURS)

    assert n == 0
    refreshed = await db_session.get(Listing, listing.id)
    assert refreshed.state == ListingState.DELIVERED


@pytest.mark.asyncio
async def test_fail_stuck_listings_ignores_recently_updated_listing(db_session):
    listing = await _make_listing(db_session, state=ListingState.EXPORTING)
    await _add_job(db_session, listing, step="distribution", status=JobStatus.QUEUED, age=_FRESH)

    n = await periodic.fail_stuck_listings(make_session_factory(db_session), max_age_hours=MAX_AGE_HOURS)

    assert n == 0
    refreshed = await db_session.get(Listing, listing.id)
    assert refreshed.state == ListingState.EXPORTING


@pytest.mark.asyncio
async def test_fail_stuck_listings_sets_error_message_and_cancels_queued_jobs(db_session):
    listing = await _make_listing(db_session, state=ListingState.EXPORTING)
    await _add_job(db_session, listing, step="mls_export", status=JobStatus.DONE, age=_STALE)
    await _add_job(db_session, listing, step="distribution", status=JobStatus.QUEUED, age=_STALE)

    n = await periodic.fail_stuck_listings(make_session_factory(db_session), max_age_hours=MAX_AGE_HOURS)

    assert n == 1
    from listingjet.models.event import Event
    events = (await db_session.execute(
        select(Event).where(Event.listing_id == str(listing.id), Event.event_type == "pipeline.failed")
    )).scalars().all()
    assert len(events) == 1
    assert events[0].payload["error"] == f"pipeline timeout after {MAX_AGE_HOURS}h"

    distribution_status = (await db_session.execute(select(PipelineJob.status).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "distribution"))).scalar_one()
    assert distribution_status == JobStatus.CANCELLED
