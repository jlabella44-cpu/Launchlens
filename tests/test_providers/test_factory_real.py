"""
Verify that factory returns the correct concrete class for each provider type.
Tests use patched settings to control the use_mock_providers flag.
"""
from unittest.mock import patch

from launchlens.providers.base import LLMProvider, VisionProvider
from launchlens.providers.claude import ClaudeProvider
from launchlens.providers.factory import get_llm_provider, get_template_provider, get_vision_provider
from launchlens.providers.google_vision import GoogleVisionProvider
from launchlens.providers.mock import MockTemplateProvider


def test_factory_returns_google_vision_when_mock_disabled():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.google_vision_api_key = "test"
        provider = get_vision_provider()
        assert isinstance(provider, GoogleVisionProvider)


def test_factory_returns_claude_when_mock_disabled():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.anthropic_api_key = "test"
        provider = get_llm_provider()
        assert isinstance(provider, ClaudeProvider)


def test_factory_returns_mock_template_always():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)


def test_factory_returns_vision_provider_interface_for_google():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.google_vision_api_key = "test"
        provider = get_vision_provider()
        assert isinstance(provider, VisionProvider)


def test_factory_returns_llm_provider_interface_for_claude():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.anthropic_api_key = "test"
        provider = get_llm_provider()
        assert isinstance(provider, LLMProvider)
