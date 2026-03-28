import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from launchlens.activities.pipeline import ALL_ACTIVITIES
from launchlens.config import settings
from launchlens.workflows.demo_cleanup import DemoCleanupWorkflow, run_demo_cleanup
from launchlens.workflows.listing_pipeline import ListingPipeline


async def create_worker() -> Worker:
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    return Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ListingPipeline, DemoCleanupWorkflow],
        activities=[*ALL_ACTIVITIES, run_demo_cleanup],
    )


async def main():
    worker = await create_worker()
    print(f"Worker started on queue: {settings.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
