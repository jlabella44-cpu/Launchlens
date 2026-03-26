from temporalio import activity
from .base import BaseAgent, AgentContext


class BrandAgent(BaseAgent):
    agent_name = "brand"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("BrandAgent not yet implemented")


@activity.defn
async def run_brand(listing_id: str, tenant_id: str) -> str:
    agent = BrandAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
