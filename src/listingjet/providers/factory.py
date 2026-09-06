# src/listingjet/providers/factory.py
"""
Provider factory.

Returns mock providers when USE_MOCK_PROVIDERS=true (tests, local dev).
Returns real providers otherwise (requires API keys in environment).

No routing: each provider slot maps to exactly one real implementation.
`agent`/`tenant_id` kwargs are accepted and ignored so existing callers
need no changes.
"""
from listingjet.config import settings

from .base import ImageEditProvider, LLMProvider, TemplateProvider, VirtualStagingProvider, VisionProvider


def get_claude(agent: str | None = None, tenant_id=None):
    """Return the raw Claude client, or a mock when USE_MOCK_PROVIDERS is set."""
    if settings.use_mock_providers:
        from .mock import MockClaudeClient
        return MockClaudeClient()
    from .claude import ClaudeClient
    return ClaudeClient()


def get_llm_provider(agent: str | None = None, tenant_id=None) -> LLMProvider:
    """Return the LLM provider (Claude), or a mock when USE_MOCK_PROVIDERS is set."""
    if settings.use_mock_providers:
        from .mock import MockLLMProvider
        return MockLLMProvider()
    from .claude import ClaudeProvider
    return ClaudeProvider(client=get_claude(agent=agent, tenant_id=tenant_id))


def get_vision_provider(agent: str | None = None, tenant_id=None) -> VisionProvider:
    """Return the Tier 1 vision provider (Google Vision), or a mock when USE_MOCK_PROVIDERS is set."""
    if settings.use_mock_providers:
        from .mock import MockVisionProvider
        return MockVisionProvider()
    from .google_vision import GoogleVisionProvider
    return GoogleVisionProvider()


def get_tier2_vision_provider(agent: str | None = None, tenant_id=None) -> VisionProvider:
    """Return the Tier 2 vision provider (OpenAI Vision), or a mock when USE_MOCK_PROVIDERS is set."""
    if settings.use_mock_providers:
        from .mock import MockVisionProvider
        return MockVisionProvider()
    from .openai_vision import OpenAIVisionProvider
    return OpenAIVisionProvider()


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
