"""Tests for per-agent provider routing and factory dispatch."""
from unittest.mock import patch

from listingjet.providers import _routing
from listingjet.providers.base import LLMProvider, VisionProvider
from listingjet.providers.factory import get_llm_provider, get_vision_provider
from listingjet.providers.fallback import FallbackLLMProvider


def _patched_settings(**overrides):
    defaults = {
        "use_mock_providers": False,
        "llm_provider": "claude",
        "vision_provider_tier1": "google",
        "agent_model_routing": "",
        "tenant_model_routing": "",
        "llm_fallback_enabled": False,
        "llm_shadow_mode": False,
        "llm_shadow_similarity_threshold": 0.5,
        "qwen_enable_cache": False,
        "gemma_base_url": "",
        "gemma_model": "gemma-4-31b-it",
        "anthropic_api_key": "test",
        "google_vision_api_key": "test",
        "qwen_api_key": "test",
        "gemini_api_key": "test",
        "openai_api_key": "test",
    }
    defaults.update(overrides)
    return defaults


def _patch(**overrides):
    values = _patched_settings(**overrides)
    patches = [
        patch("listingjet.providers.factory.settings", **{"configure_mock": None}),
        patch("listingjet.providers._routing.settings", **{"configure_mock": None}),
    ]
    ctxs = [p.start() for p in patches]
    for ctx in ctxs:
        for k, v in values.items():
            setattr(ctx, k, v)
    return patches


def test_global_llm_provider_qwen():
    patches = _patch(llm_provider="qwen")
    try:
        provider = get_llm_provider()
        assert type(provider).__name__ == "QwenProvider"
        assert isinstance(provider, LLMProvider)
    finally:
        for p in patches:
            p.stop()


def test_global_llm_provider_gemma():
    patches = _patch(llm_provider="gemma")
    try:
        provider = get_llm_provider()
        assert type(provider).__name__ == "GemmaProvider"
    finally:
        for p in patches:
            p.stop()


def test_agent_override_llm():
    routing = '{"llm": {"floorplan": "qwen", "social_content": "gemma"}}'
    patches = _patch(llm_provider="claude", agent_model_routing=routing)
    try:
        assert type(get_llm_provider("floorplan")).__name__ == "QwenProvider"
        assert type(get_llm_provider("social_content")).__name__ == "GemmaProvider"
        assert type(get_llm_provider("content")).__name__ == "ClaudeProvider"
        assert type(get_llm_provider()).__name__ == "ClaudeProvider"
    finally:
        for p in patches:
            p.stop()


def test_agent_override_vision():
    routing = '{"vision": {"photo_compliance": "gemma"}}'
    patches = _patch(vision_provider_tier1="google", agent_model_routing=routing)
    try:
        assert type(get_vision_provider("photo_compliance")).__name__ == "GemmaVisionProvider"
        assert type(get_vision_provider("other")).__name__ == "GoogleVisionProvider"
        assert isinstance(get_vision_provider(), VisionProvider)
    finally:
        for p in patches:
            p.stop()


def test_llm_fallback_wraps_primary():
    patches = _patch(llm_provider="qwen", llm_fallback_enabled=True)
    try:
        provider = get_llm_provider()
        assert isinstance(provider, FallbackLLMProvider)
        assert type(provider.primary).__name__ == "QwenProvider"
        assert type(provider.fallback).__name__ == "ClaudeProvider"
    finally:
        for p in patches:
            p.stop()


def test_llm_fallback_noop_for_claude():
    patches = _patch(llm_provider="claude", llm_fallback_enabled=True)
    try:
        provider = get_llm_provider()
        assert type(provider).__name__ == "ClaudeProvider"
    finally:
        for p in patches:
            p.stop()


def test_invalid_routing_json_is_ignored():
    patches = _patch(llm_provider="claude", agent_model_routing="not-json")
    try:
        assert type(get_llm_provider("floorplan")).__name__ == "ClaudeProvider"
    finally:
        for p in patches:
            p.stop()


def test_resolve_llm_provider_falls_back_to_global():
    with patch.object(_routing, "settings") as s:
        s.agent_model_routing = ""
        s.llm_provider = "gemma"
        assert _routing.resolve_llm_provider("floorplan") == "gemma"
        assert _routing.resolve_llm_provider(None) == "gemma"


def test_tenant_override_beats_agent_override():
    routing = {
        "tenant_model_routing": '{"t-1": {"llm": "claude"}}',
        "agent_model_routing": '{"llm": {"floorplan": "qwen"}}',
        "llm_provider": "gemma",
    }
    patches = _patch(**routing)
    try:
        # tenant default "claude" beats global "gemma" AND agent override "qwen"
        assert type(get_llm_provider("floorplan", tenant_id="t-1")).__name__ == "ClaudeProvider"
        # no tenant -> agent override still wins over global
        assert type(get_llm_provider("floorplan")).__name__ == "QwenProvider"
    finally:
        for p in patches:
            p.stop()


def test_tenant_per_agent_override():
    routing = {
        "tenant_model_routing": '{"t-2": {"llm": "claude", "llm_per_agent": {"social_content": "gemma"}}}',
        "llm_provider": "qwen",
    }
    patches = _patch(**routing)
    try:
        assert type(get_llm_provider("social_content", tenant_id="t-2")).__name__ == "GemmaProvider"
        assert type(get_llm_provider("content", tenant_id="t-2")).__name__ == "ClaudeProvider"
        # unknown tenant falls through to global
        assert type(get_llm_provider("content", tenant_id="t-unknown")).__name__ == "QwenProvider"
    finally:
        for p in patches:
            p.stop()


def test_tenant_vision_override():
    routing = {
        "tenant_model_routing": '{"t-3": {"vision": "qwen"}}',
        "vision_provider_tier1": "google",
    }
    patches = _patch(**routing)
    try:
        assert type(get_vision_provider("vision", tenant_id="t-3")).__name__ == "QwenVisionProvider"
        assert type(get_vision_provider("vision")).__name__ == "GoogleVisionProvider"
    finally:
        for p in patches:
            p.stop()


def test_resolve_vision_provider_uses_default():
    with patch.object(_routing, "settings") as s:
        s.agent_model_routing = '{"vision": {"x": "qwen"}}'
        assert _routing.resolve_vision_provider("x", default="google") == "qwen"
        assert _routing.resolve_vision_provider("y", default="google") == "google"
        assert _routing.resolve_vision_provider(None, default="google") == "google"
