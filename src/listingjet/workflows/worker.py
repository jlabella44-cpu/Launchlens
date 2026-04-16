import asyncio
import logging
import signal
from datetime import timedelta
from pathlib import Path

from temporalio.client import Client
from temporalio.worker import Worker

from listingjet.activities.pipeline import ALL_ACTIVITIES
from listingjet.config import settings
from listingjet.telemetry import init_tracing
from listingjet.workflows.baseline_aggregation import BaselineAggregationWorkflow, run_baseline_aggregation
from listingjet.workflows.demo_cleanup import DemoCleanupWorkflow, run_demo_cleanup
from listingjet.workflows.learning_workflow import LearningWorkflow
from listingjet.workflows.listing_pipeline import ListingPipeline

logger = logging.getLogger(__name__)

# Touch-file heartbeat — Docker/ECS checks if the file was updated recently.
# No HTTP server needed; the worker just touches this file on a loop.
HEARTBEAT_FILE = Path("/tmp/worker-heartbeat")
HEARTBEAT_INTERVAL = 15  # seconds


async def _heartbeat_loop(shutdown_event: asyncio.Event) -> None:
    """Touch the heartbeat file periodically until shutdown."""
    while not shutdown_event.is_set():
        try:
            HEARTBEAT_FILE.touch()
        except OSError:
            logger.warning("Failed to touch heartbeat file %s", HEARTBEAT_FILE)
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=HEARTBEAT_INTERVAL)
        except asyncio.TimeoutError:
            pass  # Normal — loop continues


# ---------------------------------------------------------------------------
# Temporal interceptors
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Worker creation
# ---------------------------------------------------------------------------

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
        workflows=[ListingPipeline, LearningWorkflow, DemoCleanupWorkflow, BaselineAggregationWorkflow],
        activities=[*ALL_ACTIVITIES, run_demo_cleanup, run_baseline_aggregation],
        interceptors=interceptors,
    )


# ---------------------------------------------------------------------------
# Cron schedule creation
# ---------------------------------------------------------------------------

async def _ensure_schedules(client: Client) -> None:
    """Create cron schedules if they don't already exist."""
    from temporalio.client import Schedule, ScheduleActionStartWorkflow, ScheduleIntervalSpec, ScheduleSpec

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


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

async def main():
    shutdown_event = asyncio.Event()
    shutdown_timeout = 30  # seconds

    # Create Temporal worker
    worker = await create_worker()

    # Start heartbeat touch-file loop (replaces the old HTTP health server).
    # Docker/ECS health check just runs: find /tmp/worker-heartbeat -mmin -2
    heartbeat_task = asyncio.create_task(_heartbeat_loop(shutdown_event))

    logger.info("Worker ready — connected to Temporal at %s", settings.temporal_host)

    # Ensure cron schedules exist
    await _ensure_schedules(worker.client)

    # Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def _signal_handler(sig):
        logger.info("Received signal %s — initiating graceful shutdown", sig.name)
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler, sig)

    print(f"Worker started on queue: {settings.temporal_task_queue}")

    # Run worker until shutdown signal
    worker_task = asyncio.create_task(worker.run())
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    done, _ = await asyncio.wait(
        [worker_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if shutdown_event.is_set():
        logger.info("Graceful shutdown: stopping worker (timeout=%ds)...", shutdown_timeout)
        try:
            await asyncio.wait_for(worker.shutdown(), timeout=shutdown_timeout)
            logger.info("Worker stopped gracefully")
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout reached — forcing exit")
        except Exception as exc:
            logger.error("Error during shutdown: %s", exc)

    # Cleanup
    heartbeat_task.cancel()
    try:
        HEARTBEAT_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    logger.info("Worker exit complete.")


if __name__ == "__main__":
    asyncio.run(main())
