import pytest
from launchlens.providers.base import VisionLabel, VisionProvider, LLMProvider, TemplateProvider
from launchlens.providers.mock import MockVisionProvider, MockLLMProvider, MockTemplateProvider


def test_vision_label_dataclass():
    label = VisionLabel(name="kitchen", confidence=0.95, category="room")
    assert label.name == "kitchen"
    assert label.confidence == 0.95
    assert label.category == "room"


def test_mock_vision_provider_is_vision_provider():
    provider = MockVisionProvider()
    assert isinstance(provider, VisionProvider)


def test_mock_llm_provider_is_llm_provider():
    provider = MockLLMProvider()
    assert isinstance(provider, LLMProvider)


def test_mock_template_provider_is_template_provider():
    provider = MockTemplateProvider()
    assert isinstance(provider, TemplateProvider)


@pytest.mark.asyncio
async def test_mock_vision_provider_analyze_returns_labels():
    provider = MockVisionProvider()
    labels = await provider.analyze(image_url="https://example.com/photo.jpg")
    assert isinstance(labels, list)
    assert len(labels) > 0
    assert all(isinstance(l, VisionLabel) for l in labels)


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
