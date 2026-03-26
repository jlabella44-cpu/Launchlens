from temporalio import activity
from .base import BaseAgent, AgentContext


class PackagingAgent(BaseAgent):
    agent_name = "packaging"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("PackagingAgent not yet implemented")


@activity.defn
async def run_packaging(listing_id: str, tenant_id: str) -> str:
    agent = PackagingAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
