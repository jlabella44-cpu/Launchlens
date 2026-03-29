"""Tests for BaseAgent.instrumented_execute — verifies tracing + metrics wrapping."""

from unittest.mock import patch

import pytest

from listingjet.agents.base import AgentContext, BaseAgent


class DummyAgent(BaseAgent):
    agent_name = "dummy"

    def __init__(self, result=None, error=None):
        self._result = result or {"count": 5, "status": "ok"}
        self._error = error

    async def execute(self, context: AgentContext) -> dict:
        if self._error:
            raise self._error
        return self._result


@pytest.mark.asyncio
async def test_instrumented_execute_returns_result():
    agent = DummyAgent(result={"count": 10})
    ctx = AgentContext(listing_id="lid", tenant_id="tid")
    result = await agent.instrumented_execute(ctx)
    assert result == {"count": 10}


@pytest.mark.asyncio
async def test_instrumented_execute_tracks_duration():
    agent = DummyAgent()
    ctx = AgentContext(listing_id="lid", tenant_id="tid")

    with patch("listingjet.agents.base.StepTimer") as MockTimer:
        mock_instance = MockTimer.return_value
        mock_instance.__enter__ = lambda self: self
        mock_instance.__exit__ = lambda self, *args: False

        await agent.instrumented_execute(ctx)
        MockTimer.assert_called_once_with("dummy")


@pytest.mark.asyncio
async def test_instrumented_execute_propagates_exception():
    agent = DummyAgent(error=ValueError("test"))
    ctx = AgentContext(listing_id="lid", tenant_id="tid")

    with pytest.raises(ValueError, match="test"):
        await agent.instrumented_execute(ctx)
