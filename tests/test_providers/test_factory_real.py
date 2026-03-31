"""
Verify that factory returns the correct concrete class for each provider type.
Tests use patched settings to control the use_mock_providers flag.
"""
from unittest.mock import patch

from listingjet.providers.base import LLMProvider, VisionProvider
from listingjet.providers.claude import ClaudeProvider
from listingjet.providers.factory import get_llm_provider, get_template_provider, get_vision_provider
from listingjet.providers.google_vision import GoogleVisionProvider
from listingjet.providers.mock import MockTemplateProvider


def test_factory_returns_google_vision_when_mock_disabled():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.google_vision_api_key = "test"
        provider = get_vision_provider()
        assert isinstance(provider, GoogleVisionProvider)


def test_factory_returns_claude_when_mock_disabled():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.anthropic_api_key = "test"
        provider = get_llm_provider()
        assert isinstance(provider, ClaudeProvider)


def test_factory_returns_mock_template_always():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.canva_api_key = None
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)


def test_factory_returns_vision_provider_interface_for_google():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.google_vision_api_key = "test"
        provider = get_vision_provider()
        assert isinstance(provider, VisionProvider)


def test_factory_returns_llm_provider_interface_for_claude():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.anthropic_api_key = "test"
        provider = get_llm_provider()
        assert isinstance(provider, LLMProvider)
