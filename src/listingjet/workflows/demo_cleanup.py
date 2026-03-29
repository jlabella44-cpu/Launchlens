"""
Temporal cron workflow for demo listing cleanup.

Schedule: runs every hour via Temporal cron.
Activity: deletes expired demo listings + S3 assets.
"""
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@activity.defn
async def run_demo_cleanup() -> dict:
    from listingjet.database import AsyncSessionLocal
    from listingjet.services.demo_cleanup import cleanup_expired_demos

    async with AsyncSessionLocal() as session:
        return await cleanup_expired_demos(session)


@workflow.defn
class DemoCleanupWorkflow:
    """Cron workflow — Temporal schedules this hourly."""

    @workflow.run
    async def run(self) -> dict:
        return await workflow.execute_activity(
            run_demo_cleanup,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
