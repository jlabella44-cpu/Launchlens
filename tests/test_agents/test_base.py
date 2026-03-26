# tests/test_agents/test_base.py
import pytest
from unittest.mock import AsyncMock, patch
from launchlens.agents.base import BaseAgent, AgentContext


class ConcreteAgent(BaseAgent):
    agent_name = "test_agent"

    async def execute(self, context: AgentContext):
        raise ValueError("simulated failure")


@pytest.mark.asyncio
async def test_handle_failure_emits_event_and_reraises():
    agent = ConcreteAgent()
    ctx = AgentContext(listing_id="abc", tenant_id="tenant-1")
    with patch("launchlens.agents.base.emit_event", new_callable=AsyncMock) as mock_emit:
        with pytest.raises(ValueError, match="simulated failure"):
            await agent.handle_failure(ValueError("simulated failure"), ctx)
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args[0]
        assert call_args[0] == "test_agent.failed"


@pytest.mark.asyncio
async def test_agent_name_required():
    with pytest.raises(TypeError):
        class NoNameAgent(BaseAgent):
            async def execute(self, context):
                pass
