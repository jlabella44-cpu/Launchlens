import uuid

from temporalio import activity

from launchlens.database import AsyncSessionLocal
from launchlens.models.listing import Listing, ListingState
from launchlens.services.events import emit_event

from .base import AgentContext, BaseAgent


class DistributionAgent(BaseAgent):
    agent_name = "distribution"

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def execute(self, context: AgentContext) -> dict:
        listing_id = uuid.UUID(context.listing_id)

        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                listing = await session.get(Listing, listing_id)
                listing.state = ListingState.DELIVERED

                await emit_event(
                    session=session,
                    event_type="pipeline.completed",
                    payload={"listing_id": context.listing_id},
                    tenant_id=context.tenant_id,
                    listing_id=context.listing_id,
                )

                # Send pipeline-complete notification email
                from launchlens.services.notifications import notify_pipeline_complete
                await notify_pipeline_complete(session, listing, context.tenant_id)

        return {"status": "delivered"}


@activity.defn
async def run_distribution(listing_id: str, tenant_id: str) -> dict:
    agent = DistributionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
