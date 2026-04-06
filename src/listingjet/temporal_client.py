from temporalio.client import Client

from listingjet.config import settings
from listingjet.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput


class TemporalClient:
    def __init__(self):
        self._client: Client | None = None

    async def _connect(self) -> Client:
        if self._client is None:
            self._client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        return self._client

    async def start_pipeline(
        self,
        listing_id: str,
        tenant_id: str,
        plan: str = "starter",
        billing_model: str = "legacy",
        enabled_addons: list[str] | None = None,
    ) -> str:
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        handle = await client.start_workflow(
            ListingPipeline.run,
            ListingPipelineInput(
                listing_id=listing_id,
                tenant_id=tenant_id,
                plan=plan,
                billing_model=billing_model,
                enabled_addons=enabled_addons,
            ),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        return handle.id

    async def signal_review_completed(self, listing_id: str) -> None:
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(ListingPipeline.human_review_completed)


_temporal_client: TemporalClient | None = None


def get_temporal_client() -> TemporalClient:
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = TemporalClient()
    return _temporal_client
