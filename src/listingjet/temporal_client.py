import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.service import RPCError

from listingjet.config import settings
from listingjet.workflows.listing_pipeline import ListingPipeline, ListingPipelineInput

logger = logging.getLogger(__name__)


async def connect_temporal(**overrides) -> Client:
    """Connect to Temporal, honoring Temporal Cloud auth from settings.

    Single source of truth for how every entrypoint (API client, worker,
    health check) reaches Temporal. When ``temporal_api_key`` is set we are
    talking to Temporal Cloud, which requires TLS — so TLS is enabled
    automatically whenever an API key is present (and can also be forced on
    via ``temporal_tls`` for mTLS / TLS-fronted self-hosted clusters).

    ``overrides`` are merged last so callers can pass extras like
    ``interceptors=...`` without duplicating the auth wiring.
    """
    kwargs: dict = {"namespace": settings.temporal_namespace}
    if settings.temporal_api_key:
        kwargs["api_key"] = settings.temporal_api_key
    if settings.temporal_tls or settings.temporal_api_key:
        kwargs["tls"] = True
    kwargs.update(overrides)
    return await Client.connect(settings.temporal_host, **kwargs)


class TemporalClient:
    def __init__(self):
        self._client: Client | None = None

    async def _connect(self) -> Client:
        if self._client is None:
            self._client = await connect_temporal()
        return self._client

    async def start_pipeline(
        self,
        listing_id: str,
        tenant_id: str,
        plan: str = "starter",
        billing_model: str = "legacy",
        enabled_addons: list[str] | None = None,
        terminate_existing: bool = False,
    ) -> str:
        """Start the listing pipeline workflow.

        ``terminate_existing=True`` is for retry: if an old workflow with the
        same ID is still running (stuck/stalled) it is terminated and a new
        one takes the slot. Without this, ``REJECT_DUPLICATE`` causes
        "already started" to be swallowed and the retry silently no-ops.
        """
        client = await self._connect()
        workflow_id = f"listing-pipeline-{listing_id}"
        reuse_policy = (
            WorkflowIDReusePolicy.TERMINATE_IF_RUNNING
            if terminate_existing
            else WorkflowIDReusePolicy.REJECT_DUPLICATE
        )
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
                id_reuse_policy=reuse_policy,
            )
            return handle.id
        except RPCError as exc:
            if not terminate_existing and "already started" in str(exc).lower():
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


_temporal_client: TemporalClient | None = None


def get_temporal_client() -> TemporalClient:
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = TemporalClient()
    return _temporal_client
