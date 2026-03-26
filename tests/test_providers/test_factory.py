import pytest
from unittest.mock import patch
from launchlens.providers.factory import get_vision_provider, get_llm_provider, get_template_provider
from launchlens.providers.mock import MockVisionProvider, MockLLMProvider, MockTemplateProvider
from launchlens.providers.base import VisionProvider, LLMProvider, TemplateProvider


def test_get_vision_provider_returns_mock_when_flag_set():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_vision_provider()
        assert isinstance(provider, MockVisionProvider)


def test_get_llm_provider_returns_mock_when_flag_set():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)


def test_get_template_provider_returns_mock_when_flag_set():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)


def test_get_vision_provider_returns_vision_provider_interface():
    with patch("launchlens.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_vision_provider()
        assert isinstance(provider, VisionProvider)
