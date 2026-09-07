"""Periodic maintenance tasks run in-process by `pipeline.runner.periodic_loop`.

These run as plain coroutines on the pipeline worker's own schedule. Both
open an `admin_session()` (not `AsyncSessionLocal`) because they are system
actors that read/write across tenants.
"""


async def run_demo_cleanup() -> dict:
    from listingjet.database import admin_session
    from listingjet.services.demo_cleanup import cleanup_expired_demos
    from listingjet.services.storage import get_storage

    async with admin_session() as session:
        return await cleanup_expired_demos(session, storage=get_storage())


async def run_baseline_aggregation() -> dict:
    """Average LearningWeight across tenants per room_label into GlobalBaselineWeight."""
    from sqlalchemy import func, select

    from listingjet.database import admin_session
    from listingjet.models.global_baseline_weight import GlobalBaselineWeight
    from listingjet.models.learning_weight import LearningWeight

    async with admin_session() as session:
        async with session.begin():
            # Average weight per room_label across all tenants
            result = await session.execute(
                select(
                    LearningWeight.room_label,
                    func.avg(LearningWeight.weight).label("avg_weight"),
                    func.count(LearningWeight.id).label("tenant_count"),
                )
                .group_by(LearningWeight.room_label)
                .having(func.count(LearningWeight.id) >= 3)  # Minimum 3 tenants for signal
            )
            rows = result.all()

            updated = 0
            for room_label, avg_weight, tenant_count in rows:
                existing = (await session.execute(
                    select(GlobalBaselineWeight).where(
                        GlobalBaselineWeight.room_label == room_label
                    )
                )).scalar_one_or_none()

                if existing:
                    existing.weight = round(float(avg_weight), 4)
                    existing.updated_at = func.now()
                else:
                    session.add(GlobalBaselineWeight(
                        room_label=room_label,
                        weight=round(float(avg_weight), 4),
                    ))
                updated += 1

    return {"updated": updated, "room_labels": len(rows)}


async def fail_stuck_listings(session_factory=None, *, max_age_hours: int) -> int:
    """Fail any listing whose pipeline has been silently stuck for too long.

    A listing in UPLOADING/ANALYZING/EXPORTING with no RUNNING job and whose
    newest `pipeline_jobs.updated_at` is older than `max_age_hours` has no
    worker actively making progress on it and none queued to reclaim it (that's
    `reclaim_stale`'s job, and it only handles RUNNING rows) — most likely a bug
    silently dropped every job for the listing without ever failing it. A
    listing with zero `pipeline_jobs` rows at all (enqueue itself never ran)
    is caught the same way, falling back to the listing's own `updated_at`.
    Moves the listing to PIPELINE_TIMEOUT via `runner.fail_listing` (which also
    cancels any still-QUEUED/WAITING rows) and returns the number failed.
    """
    from datetime import timedelta

    from sqlalchemy import func, select

    from listingjet.database import admin_session
    from listingjet.models.listing import Listing, ListingState
    from listingjet.models.pipeline_job import JobStatus, PipelineJob
    from listingjet.pipeline.runner import _now, fail_listing

    cutoff = _now() - timedelta(hours=max_age_hours)
    stuck_states = (ListingState.UPLOADING, ListingState.ANALYZING, ListingState.EXPORTING)

    async with admin_session(session_factory) as session:
        stats = (
            select(
                PipelineJob.listing_id,
                func.max(PipelineJob.updated_at).label("newest"),
                func.bool_or(PipelineJob.status == JobStatus.RUNNING).label("has_running"),
            )
            .group_by(PipelineJob.listing_id)
            .subquery()
        )
        listings = (await session.execute(
            select(Listing)
            .outerjoin(stats, stats.c.listing_id == Listing.id)
            .where(
                Listing.state.in_(stuck_states),
                func.coalesce(stats.c.has_running, False).is_(False),
                func.coalesce(stats.c.newest, Listing.updated_at) < cutoff,
            )
        )).scalars().all()

        count = 0
        for listing in listings:
            await fail_listing(
                session, listing.id, step="pipeline",
                error=f"pipeline timeout after {max_age_hours}h",
                state=ListingState.PIPELINE_TIMEOUT,
            )
            count += 1
        await session.commit()

    return count
