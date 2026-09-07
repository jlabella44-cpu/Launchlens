import pytest

from listingjet.providers.base import TemplateProvider
from listingjet.providers.mock import MockTemplateProvider


def test_mock_template_provider_is_template_provider():
    provider = MockTemplateProvider()
    assert isinstance(provider, TemplateProvider)


@pytest.mark.asyncio
async def test_mock_template_provider_render_returns_bytes():
    provider = MockTemplateProvider()
    result = await provider.render(template_id="flyer-standard", data={"headline": "Beautiful Home"})
    assert isinstance(result, bytes)
    assert len(result) > 0
