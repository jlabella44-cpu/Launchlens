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
    mock_session = AsyncMock()
    with patch("launchlens.services.events.emit_event", new_callable=AsyncMock) as mock_emit:
        with pytest.raises(ValueError, match="simulated failure"):
            await agent.handle_failure(ValueError("simulated failure"), ctx, session=mock_session)
        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["event_type"] == "test_agent.failed"


@pytest.mark.asyncio
async def test_handle_failure_without_session_still_reraises():
    agent = ConcreteAgent()
    ctx = AgentContext(listing_id="abc", tenant_id="tenant-1")
    # No session — should still re-raise without calling emit_event
    with pytest.raises(ValueError, match="simulated failure"):
        await agent.handle_failure(ValueError("simulated failure"), ctx)


@pytest.mark.asyncio
async def test_agent_name_required():
    with pytest.raises(TypeError):
        class NoNameAgent(BaseAgent):
            async def execute(self, context):
                pass
