from unittest.mock import patch

from listingjet.providers.factory import get_template_provider
from listingjet.providers.mock import MockTemplateProvider


def test_get_template_provider_returns_mock_when_flag_set():
    with patch("listingjet.providers.factory.settings") as mock_settings:
        mock_settings.use_mock_providers = True
        provider = get_template_provider()
        assert isinstance(provider, MockTemplateProvider)
