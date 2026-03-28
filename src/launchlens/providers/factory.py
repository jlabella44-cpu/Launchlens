# src/launchlens/providers/factory.py
"""
Provider factory.

Returns mock providers when USE_MOCK_PROVIDERS=true (tests, local dev).
Returns real providers otherwise (requires API keys in environment).
"""
from launchlens.config import settings

from .base import LLMProvider, TemplateProvider, VisionProvider


def get_vision_provider() -> VisionProvider:
    if settings.use_mock_providers:
        from .mock import MockVisionProvider
        return MockVisionProvider()
    from .google_vision import GoogleVisionProvider
    return GoogleVisionProvider()


def get_llm_provider() -> LLMProvider:
    if settings.use_mock_providers:
        from .mock import MockLLMProvider
        return MockLLMProvider()
    from .claude import ClaudeProvider
    return ClaudeProvider()


def get_template_provider() -> TemplateProvider:
    if settings.use_mock_providers:
        from .mock import MockTemplateProvider
        return MockTemplateProvider()
    from .mock import MockTemplateProvider  # Canva not yet implemented
    return MockTemplateProvider()
