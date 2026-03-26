from temporalio import activity
from .base import BaseAgent, AgentContext


class ContentAgent(BaseAgent):
    agent_name = "content"

    async def execute(self, context: AgentContext):
        raise NotImplementedError("ContentAgent not yet implemented")


@activity.defn
async def run_content(listing_id: str, tenant_id: str) -> str:
    agent = ContentAgent()
    ctx = AgentContext(listing_id=listing_id, tenant_id=tenant_id)
    return await agent.execute(ctx)
