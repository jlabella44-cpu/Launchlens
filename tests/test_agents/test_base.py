# tests/test_agents/test_base.py
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from listingjet.agents.base import (
    AgentContext,
    BaseAgent,
    heartbeat_during,
    parse_llm_json,
)


class ConcreteAgent(BaseAgent):
    agent_name = "test_agent"

    async def execute(self, context: AgentContext):
        raise ValueError("simulated failure")


@pytest.mark.asyncio
async def test_handle_failure_emits_event_and_reraises():
    agent = ConcreteAgent()
    ctx = AgentContext(listing_id="abc", tenant_id="tenant-1")
    mock_session = AsyncMock()
    # Return None from session.get so the notify_pipeline_failed branch is
    # skipped — otherwise the mock leaks an unawaited coroutine when the
    # notification path tries to use the session's sync methods.
    mock_session.get = AsyncMock(return_value=None)
    with patch("listingjet.services.events.emit_event", new_callable=AsyncMock) as mock_emit:
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


class TestParseLLMJSON:
    def test_returns_none_for_none(self):
        assert parse_llm_json(None) is None

    def test_returns_none_for_empty_string(self):
        assert parse_llm_json("") is None

    def test_returns_none_for_whitespace(self):
        assert parse_llm_json("   \n\t  ") is None

    def test_parses_plain_json_object(self):
        assert parse_llm_json('{"a": 1}') == {"a": 1}

    def test_parses_plain_json_array(self):
        assert parse_llm_json('[1, 2, 3]') == [1, 2, 3]

    def test_parses_json_with_markdown_fences(self):
        assert parse_llm_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_parses_json_with_unlabeled_fences(self):
        assert parse_llm_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_returns_none_for_empty_fenced_block(self):
        assert parse_llm_json('```json\n\n```') is None

    def test_returns_none_for_malformed_json(self):
        assert parse_llm_json('{not valid json}') is None

    def test_returns_none_for_prose(self):
        assert parse_llm_json("Sorry, I can't help with that.") is None

    def test_returns_none_for_truncated_json(self):
        assert parse_llm_json('{"a": 1') is None

    def test_handles_non_string_gracefully(self):
        # Some providers return ints/None when their wrapper degrades.
        assert parse_llm_json(0) is None  # type: ignore[arg-type]


class TestHeartbeatDuring:
    @pytest.mark.asyncio
    async def test_no_op_outside_temporal_activity(self):
        """Outside a Temporal activity context, _safe_heartbeat raises
        RuntimeError internally; the helper must swallow it cleanly."""
        async with heartbeat_during(interval=0.01, detail="test"):
            await asyncio.sleep(0.05)
        # No exception = pass

    @pytest.mark.asyncio
    async def test_sends_heartbeats_at_interval(self):
        """When wrapping a long-running block, heartbeats fire periodically."""
        with patch("listingjet.agents.base._safe_heartbeat") as mock_hb:
            async with heartbeat_during(interval=0.05, detail="test"):
                await asyncio.sleep(0.18)
        # Expect ~3-4 heartbeats over 180ms with 50ms interval.
        assert mock_hb.call_count >= 2

    @pytest.mark.asyncio
    async def test_heartbeat_task_cleaned_up_on_exit(self):
        """The internal heartbeat loop must not leak past the context."""
        before = len(asyncio.all_tasks())
        async with heartbeat_during(interval=0.01):
            assert len(asyncio.all_tasks()) == before + 1
        await asyncio.sleep(0)  # let cancellation propagate
        assert len(asyncio.all_tasks()) == before

    @pytest.mark.asyncio
    async def test_block_exception_propagates(self):
        """If the wrapped block raises, the exception is not swallowed."""
        with pytest.raises(ValueError, match="boom"):
            async with heartbeat_during(interval=0.01):
                raise ValueError("boom")
