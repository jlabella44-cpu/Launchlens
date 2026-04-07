from unittest.mock import patch

from listingjet.providers.base import VisionProvider
from listingjet.providers.factory import get_llm_provider, get_template_provider, get_tier2_vision_provider, get_vision_provider
from listingjet.providers.mock import MockLLMProvider, MockTemplateProvider, MockVisionProvider


def test_get_vision_provider_returns_mock_when_flag_set():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_vision_provider()
        assert isinstance(provider, MockVisionProvider)


def test_get_llm_provider_returns_mock_when_flag_set():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)


def test_get_template_provider_returns_mock_when_flag_set():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)


def test_get_vision_provider_returns_vision_provider_interface():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_vision_provider()
        assert isinstance(provider, VisionProvider)


def test_get_tier2_vision_provider_returns_mock_when_flag_set():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_tier2_vision_provider()
        assert isinstance(provider, MockVisionProvider)


def test_get_tier2_vision_provider_returns_qwen_when_dashscope_key_set():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.dashscope_api_key = "sk-test-dashscope"
        mock_settings.dashscope_base_url = "https://test.example.com/v1"
        provider = get_tier2_vision_provider()
        from listingjet.providers.qwen_vision import QwenVisionProvider
        assert isinstance(provider, QwenVisionProvider)


def test_get_tier2_vision_provider_falls_back_to_openai():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.dashscope_api_key = ""
        mock_settings.openai_api_key = "sk-test-openai"
        provider = get_tier2_vision_provider()
        from listingjet.providers.openai_vision import OpenAIVisionProvider
        assert isinstance(provider, OpenAIVisionProvider)
