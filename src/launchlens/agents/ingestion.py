from temporalio import activity
from .base import BaseAgent, AgentContext


class IngestionAgent(BaseAgent):
    agent_name = "ingestion"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("IngestionAgent not yet implemented")


@activity.defn
async def ingest_photos(listing_id: str, tenant_id: str) -> str:
    agent = IngestionAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
