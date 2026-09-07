"""
Verify that factory returns the correct concrete class for each provider type.
Tests use patched settings to control the use_mock_providers flag.
"""
from unittest.mock import patch

from listingjet.providers.factory import get_template_provider
from listingjet.providers.mock import MockTemplateProvider


def test_factory_returns_mock_template_always():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = False
        mock_settings.canva_api_key = None
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)
