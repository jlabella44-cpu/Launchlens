import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.service import RPCError

from listingjet.config import settings
from listingjet.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput

logger = logging.getLogger(__name__)


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
        try:
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
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
            return handle.id
        except RPCError as exc:
            if "already started" in str(exc).lower():
                logger.warning(
                    "Workflow already running for listing %s, returning existing handle",
                    listing_id,
                )
                return workflow_id
            raise

    async def signal_review_completed(self, listing_id: str) -> None:
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(ListingPipeline.human_review_completed)

    async def signal_shadow_review_approved(self, listing_id: str) -> None:
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(ListingPipeline.shadow_review_approved)

    async def cancel_workflow(self, listing_id: str) -> None:
        """Request cancellation of the listing pipeline workflow.

        Best-effort — swallows RPCError if the workflow is already
        completed, not found, or not running.
        """
        try:
            client = await self._connect()
            workflow_id = f"listing-pipeline-{listing_id}"
            handle = client.get_workflow_handle(workflow_id)
            await handle.cancel()
        except Exception:
            logger.debug("cancel_workflow noop listing=%s", listing_id)


_temporal_client: TemporalClient | None = None


def get_temporal_client() -> TemporalClient:
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = TemporalClient()
    return _temporal_client
