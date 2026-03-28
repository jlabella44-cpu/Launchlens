import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from launchlens.activities.pipeline import ALL_ACTIVITIES
from launchlens.config import settings
from launchlens.telemetry import init_tracing
from launchlens.workflows.demo_cleanup import DemoCleanupWorkflow, run_demo_cleanup
from launchlens.workflows.listing_pipeline import ListingPipeline

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
        workflows=[ListingPipeline, DemoCleanupWorkflow],
        activities=[*ALL_ACTIVITIES, run_demo_cleanup],
        interceptors=interceptors,
    )


async def main():
    worker = await create_worker()
    print(f"Worker started on queue: {settings.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
