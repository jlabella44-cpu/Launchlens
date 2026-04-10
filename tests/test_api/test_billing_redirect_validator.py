"""Unit tests for billing._validate_redirect_url.

These are DB-free — they exercise the standalone validator so the allowlist
regex is regression-protected (prevents reintroducing the "Redirect URL not
allowed" 400 that broke the pricing page's Stripe checkout).
"""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from listingjet.api.billing import _validate_redirect_url


class _FakeSettings:
    def __init__(self, cors_origins: str):
        self.cors_origins = cors_origins


@pytest.fixture
def narrow_cors(monkeypatch):
    """Default cors_origins contains only localhost — real production domains must
    be accepted via the hardcoded regex fallback, not via env var."""
    fake = _FakeSettings("http://localhost:3000")
    with patch("listingjet.api.billing.settings", fake):
        yield


# ── Accepted origins ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:3000/billing?success=true",
        "http://localhost:3000/",
        "https://app.listingjet.com/billing?success=true",
        "https://listingjet.com/pricing",
        "https://app.listingjet.ai/billing",
        "https://api.listingjet.ai/webhook",
        "https://listingjet.ai/",
        "https://broker-abc.listingjet.com/dashboard",  # white-label subdomain
        "https://listingjet-preview-pr-42.vercel.app/billing",
    ],
)
def test_accepts_known_safe_origins(narrow_cors, url):
    # Should not raise
    _validate_redirect_url(url)


# ── Rejected origins ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/billing",
        "https://listingjet.evil.com/billing",  # not a real subdomain of listingjet
        "http://app.listingjet.com/billing",  # http, not https
        "https://app.listingjet.net/billing",  # wrong TLD
        "https://listingjetevil.com/billing",  # no-separator typosquat
        "https://preview-pr-42.vercel.app/billing",  # vercel but wrong prefix
        "https://attacker.vercel.app/billing",
        "ftp://app.listingjet.com/billing",  # wrong scheme
    ],
)
def test_rejects_untrusted_origins(narrow_cors, url):
    with pytest.raises(HTTPException) as exc:
        _validate_redirect_url(url)
    assert exc.value.status_code == 400
    assert "Redirect URL not allowed" in exc.value.detail


def test_accepts_origin_from_env_var(monkeypatch):
    """Explicit env-var CORS origins still work alongside the regex."""
    fake = _FakeSettings("https://custom.example.com,http://localhost:3000")
    with patch("listingjet.api.billing.settings", fake):
        _validate_redirect_url("https://custom.example.com/billing")


def test_strips_trailing_slash_when_matching(monkeypatch):
    """cors_origins entries with trailing slashes should still match."""
    fake = _FakeSettings("https://app.example.com/")
    with patch("listingjet.api.billing.settings", fake):
        _validate_redirect_url("https://app.example.com/billing")
