# src/listingjet/providers/factory.py
"""
Provider factory.

Returns mock providers when USE_MOCK_PROVIDERS=true (tests, local dev).
Returns real providers otherwise (requires API keys in environment).
"""
from listingjet.config import settings

from .base import ImageEditProvider, LLMProvider, TemplateProvider, VirtualStagingProvider, VisionProvider


def _build_llm(name: str) -> LLMProvider:
    if name == "qwen":
        from .qwen import QwenProvider
        return QwenProvider()
    if name == "gemma":
        from .gemma import GemmaProvider
        return GemmaProvider()
    from .claude import ClaudeProvider
    return ClaudeProvider()


def _build_vision(name: str) -> VisionProvider:
    if name == "gemma":
        from .gemma import GemmaVisionProvider
        return GemmaVisionProvider()
    if name == "qwen":
        from .qwen import QwenVisionProvider
        return QwenVisionProvider()
    if name == "openai":
        from .openai_vision import OpenAIVisionProvider
        return OpenAIVisionProvider()
    from .google_vision import GoogleVisionProvider
    return GoogleVisionProvider()


def get_vision_provider(
    agent: str | None = None,
    tenant_id=None,
    tier: str = "tier1",
) -> VisionProvider:
    """Return a vision provider, optionally routed by agent name and tenant.

    ``tier`` selects the default when no per-agent/tenant override applies:
    "tier1" -> VISION_PROVIDER_TIER1 (cheap bulk, default)
    "tier2" -> VISION_PROVIDER_TIER2 (higher-quality analysis)
    """
    if settings.use_mock_providers:
        from .mock import MockVisionProvider
        return MockVisionProvider()
    from ._routing import resolve_vision_provider
    default = (
        settings.vision_provider_tier2 if tier == "tier2"
        else settings.vision_provider_tier1
    )
    name = resolve_vision_provider(agent, default=default, tenant_id=tenant_id)
    return _build_vision(name)


def get_llm_provider(agent: str | None = None, tenant_id=None) -> LLMProvider:
    """Return an LLM provider, optionally routed by agent name and tenant.

    When LLM_FALLBACK_ENABLED=true the returned provider transparently
    falls back to Claude if the primary call fails.
    """
    if settings.use_mock_providers:
        from .mock import MockLLMProvider
        return MockLLMProvider()
    from ._routing import resolve_llm_provider
    name = resolve_llm_provider(agent, tenant_id=tenant_id)
    primary = _build_llm(name)
    if settings.llm_shadow_mode and name != "claude":
        from .claude import ClaudeProvider
        from .shadow import ShadowLLMProvider
        primary = ShadowLLMProvider(
            primary=primary,
            truth=ClaudeProvider(),
            similarity_threshold=settings.llm_shadow_similarity_threshold,
            label=agent or name,
        )
    if settings.llm_fallback_enabled and name != "claude":
        from .claude import ClaudeProvider
        from .fallback import FallbackLLMProvider
        return FallbackLLMProvider(primary=primary, fallback=ClaudeProvider())
    return primary


def get_image_edit_provider() -> ImageEditProvider:
    if settings.use_mock_providers:
        from .mock import MockImageEditProvider
        return MockImageEditProvider()
    from .openai_image_edit import OpenAIImageEditProvider
    return OpenAIImageEditProvider()


def get_virtual_staging_provider() -> VirtualStagingProvider:
    if settings.use_mock_providers:
        from .mock import MockVirtualStagingProvider
        return MockVirtualStagingProvider()
    from .openai_staging import OpenAIVirtualStagingProvider
    return OpenAIVirtualStagingProvider()


def get_template_provider() -> TemplateProvider:
    if settings.use_mock_providers:
        from .mock import MockTemplateProvider
        return MockTemplateProvider()
    if settings.canva_api_key:
        from .canva import CanvaTemplateProvider
        return CanvaTemplateProvider(api_key=settings.canva_api_key, llm_provider=get_llm_provider())
    from .mock import MockTemplateProvider
    return MockTemplateProvider()
