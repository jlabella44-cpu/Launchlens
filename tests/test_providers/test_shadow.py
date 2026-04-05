"""Tests for ShadowLLMProvider."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from listingjet.providers.base import LLMProvider
from listingjet.providers.shadow import ShadowLLMProvider, _similarity


class _Stub(LLMProvider):
    def __init__(self, result):
        self._result = result
        self.calls = 0

    async def complete(self, prompt, context, temperature=None, system_prompt=None):
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def test_similarity_identical():
    assert _similarity("the cozy blue home", "the cozy blue home") == 1.0


def test_similarity_disjoint():
    assert _similarity("abc def", "xyz qrs") == 0.0


def test_similarity_partial():
    # overlap {"cozy","home"}, union {"the","cozy","home","beautiful","large"}
    assert _similarity("the cozy home", "cozy beautiful large home") == pytest.approx(2 / 5)


@pytest.mark.asyncio
async def test_shadow_returns_primary_result():
    primary = _Stub("cheap answer")
    truth = _Stub("premium answer")
    shadow = ShadowLLMProvider(primary, truth)
    with patch("listingjet.monitoring.metrics.emit_metric"):
        result = await shadow.complete("p", {})
    assert result == "cheap answer"
    # Allow the background compare task to run
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert primary.calls == 1
    assert truth.calls == 1


@pytest.mark.asyncio
async def test_shadow_truth_failure_does_not_raise():
    primary = _Stub("cheap answer")
    truth = _Stub(RuntimeError("boom"))
    shadow = ShadowLLMProvider(primary, truth)
    with patch("listingjet.monitoring.metrics.emit_metric"):
        result = await shadow.complete("p", {})
    assert result == "cheap answer"
    await asyncio.sleep(0)
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_shadow_logs_divergence_when_below_threshold(caplog):
    primary = _Stub("one two three")
    truth = _Stub("completely different response")
    shadow = ShadowLLMProvider(primary, truth, similarity_threshold=0.9, label="test")
    caplog.set_level("INFO")
    with patch("listingjet.monitoring.metrics.emit_metric") as emit:
        await shadow.complete("p", {})
        # wait for background task
        for _ in range(5):
            await asyncio.sleep(0)
    assert any("divergence" in r.message for r in caplog.records)
    assert emit.called


@pytest.mark.asyncio
async def test_shadow_no_log_when_above_threshold():
    primary = _Stub("same words here exactly")
    truth = _Stub("same words here exactly")
    shadow = ShadowLLMProvider(primary, truth, similarity_threshold=0.5)
    with patch("listingjet.monitoring.metrics.emit_metric") as emit, \
         patch("listingjet.providers.shadow.logger") as log:
        await shadow.complete("p", {})
        for _ in range(5):
            await asyncio.sleep(0)
    # emitted metric but did not .info() divergence
    assert emit.called
    divergence_logged = any(
        "divergence" in str(c) for c in log.info.call_args_list
    )
    assert not divergence_logged


@pytest.mark.asyncio
async def test_shadow_factory_wires_when_enabled():
    """get_llm_provider wraps primary in ShadowLLMProvider when flag is set."""
    from listingjet.providers.factory import get_llm_provider
    from unittest.mock import patch as upatch

    with upatch("listingjet.providers.factory.settings") as s, \
         upatch("listingjet.providers._routing.settings") as s2:
        for mock in (s, s2):
            mock.use_mock_providers = False
            mock.llm_provider = "qwen"
            mock.agent_model_routing = ""
            mock.tenant_model_routing = ""
            mock.llm_fallback_enabled = False
            mock.llm_shadow_mode = True
            mock.llm_shadow_similarity_threshold = 0.5
            mock.qwen_api_key = "k"
            mock.anthropic_api_key = "k"
            mock.qwen_enable_cache = False
        provider = get_llm_provider(agent="content")
    assert isinstance(provider, ShadowLLMProvider)
    assert type(provider.primary).__name__ == "QwenProvider"
    assert type(provider.truth).__name__ == "ClaudeProvider"


@pytest.mark.asyncio
async def test_shadow_noop_for_claude_primary():
    """Shadow mode is skipped when the primary IS Claude (no point)."""
    from listingjet.providers.factory import get_llm_provider
    from unittest.mock import patch as upatch

    with upatch("listingjet.providers.factory.settings") as s, \
         upatch("listingjet.providers._routing.settings") as s2:
        for mock in (s, s2):
            mock.use_mock_providers = False
            mock.llm_provider = "claude"
            mock.agent_model_routing = ""
            mock.tenant_model_routing = ""
            mock.llm_fallback_enabled = False
            mock.llm_shadow_mode = True
            mock.llm_shadow_similarity_threshold = 0.5
            mock.anthropic_api_key = "k"
        provider = get_llm_provider()
    assert type(provider).__name__ == "ClaudeProvider"
