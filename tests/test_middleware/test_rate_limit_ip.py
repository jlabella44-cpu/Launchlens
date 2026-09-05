from unittest.mock import patch

from starlette.requests import Request

from listingjet.middleware.rate_limit import extract_client_ip


def _req(xff: str | None) -> Request:
    headers = [(b"x-forwarded-for", xff.encode())] if xff else []
    return Request({
        "type": "http", "method": "GET", "path": "/", "headers": headers,
        "query_string": b"", "server": ("testserver", 80), "scheme": "http",
        "client": ("10.0.0.9", 1234),
    })


def test_one_trusted_proxy_uses_last_forwarded_entry():
    with patch("listingjet.middleware.rate_limit.settings.trusted_proxy_count", 1):
        assert extract_client_ip(_req("203.0.113.5, 10.1.1.1")) == "10.1.1.1"


def test_zero_trusted_proxies_ignores_header():
    with patch("listingjet.middleware.rate_limit.settings.trusted_proxy_count", 0):
        assert extract_client_ip(_req("203.0.113.5")) == "10.0.0.9"


def test_default_is_one_proxy():
    from listingjet.config import Settings
    assert Settings.model_fields["trusted_proxy_count"].default == 1
