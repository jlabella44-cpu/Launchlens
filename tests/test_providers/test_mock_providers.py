import pytest

from listingjet.providers.base import LLMProvider, TemplateProvider
from listingjet.providers.mock import MockLLMProvider, MockTemplateProvider


def test_mock_llm_provider_is_llm_provider():
    provider = MockLLMProvider()
    assert isinstance(provider, LLMProvider)


def test_mock_template_provider_is_template_provider():
    provider = MockTemplateProvider()
    assert isinstance(provider, TemplateProvider)


@pytest.mark.asyncio
async def test_mock_llm_provider_complete_returns_string():
    provider = MockLLMProvider()
    result = await provider.complete(prompt="Describe this kitchen.", context={})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_mock_template_provider_render_returns_bytes():
    provider = MockTemplateProvider()
    result = await provider.render(template_id="flyer-standard", data={"headline": "Beautiful Home"})
    assert isinstance(result, bytes)
    assert len(result) > 0
