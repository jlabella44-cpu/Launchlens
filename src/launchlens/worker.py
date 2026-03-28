import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from launchlens.config import settings
from launchlens.workflows.listing_pipeline import ListingPipeline


async def main() -> None:
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )
    async with Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ListingPipeline],
        activities=[],  # populated in Agent Pipeline plan
    ):
        print(f"Worker running on {settings.temporal_task_queue}")
        await asyncio.Event().wait()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
