import asyncio
import logging
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from listingjet.activities.pipeline import ALL_ACTIVITIES
from listingjet.config import settings
from listingjet.telemetry import init_tracing
from listingjet.workflows.baseline_aggregation import BaselineAggregationWorkflow, run_baseline_aggregation
from listingjet.workflows.demo_cleanup import DemoCleanupWorkflow, run_demo_cleanup
from listingjet.workflows.listing_pipeline import ListingPipeline

logger = logging.getLogger(__name__)


def _get_interceptors() -> list:
    """Return Temporal interceptors. Adds tracing if opentelemetry is available."""
    interceptors = []
    try:
        from temporalio.contrib.opentelemetry import TracingInterceptor

        interceptors.append(TracingInterceptor())
        logger.info("Temporal TracingInterceptor enabled")
    except ImportError:
        logger.debug("temporalio opentelemetry contrib not available — skipping tracing interceptor")
    return interceptors


async def create_worker() -> Worker:
    init_tracing()
    interceptors = _get_interceptors()
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
        interceptors=interceptors,
    )
    return Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ListingPipeline, DemoCleanupWorkflow, BaselineAggregationWorkflow],
        activities=[*ALL_ACTIVITIES, run_demo_cleanup, run_baseline_aggregation],
        interceptors=interceptors,
    )


async def _ensure_schedules(client: Client) -> None:
    """Create cron schedules if they don't already exist."""
    from temporalio.client import Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec

    schedules = [
        (
            "demo-cleanup-hourly",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    DemoCleanupWorkflow.run,
                    id="demo-cleanup",
                    task_queue=settings.temporal_task_queue,
                ),
                spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(hours=1))]),
            ),
        ),
        (
            "baseline-aggregation-weekly",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    BaselineAggregationWorkflow.run,
                    id="baseline-aggregation",
                    task_queue=settings.temporal_task_queue,
                ),
                spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(days=7))]),
            ),
        ),
    ]

    for schedule_id, schedule in schedules:
        try:
            await client.create_schedule(schedule_id, schedule)
            logger.info("Created schedule: %s", schedule_id)
        except Exception as exc:
            if "already exists" in str(exc).lower():
                logger.debug("Schedule %s already exists", schedule_id)
            else:
                logger.warning("Failed to create schedule %s: %s", schedule_id, exc)


async def main():
    worker = await create_worker()
    # Ensure cron schedules exist before starting worker loop
    await _ensure_schedules(worker.client)
    print(f"Worker started on queue: {settings.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
