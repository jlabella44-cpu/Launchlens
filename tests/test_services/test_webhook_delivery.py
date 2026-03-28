import json
from unittest.mock import AsyncMock, patch

import pytest

from launchlens.services.webhook_delivery import _is_url_safe, deliver_webhook

_SSRF_PATCH_TARGET = "launchlens.services.webhook_delivery._is_url_safe"


@pytest.mark.asyncio
async def test_successful_delivery():
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch(_SSRF_PATCH_TARGET, return_value=True), patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await deliver_webhook(
            url="https://example.com/webhook",
            event_type="pipeline.completed",
            payload={"listing_id": "abc"},
            tenant_id="tenant-123",
            listing_id="listing-456",
        )

    assert result is True
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    body = json.loads(call_kwargs.kwargs.get("content") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs["content"])
    assert body["event"] == "pipeline.completed"
    assert body["tenant_id"] == "tenant-123"


@pytest.mark.asyncio
async def test_failed_delivery_retries():
    mock_response = AsyncMock()
    mock_response.status_code = 500

    with patch(_SSRF_PATCH_TARGET, return_value=True), patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await deliver_webhook(
            url="https://example.com/webhook",
            event_type="test.event",
            payload={},
            tenant_id="t1",
        )

    assert result is False
    assert mock_client.post.call_count == 3  # 3 retries


@pytest.mark.asyncio
async def test_network_error_retries():
    with patch(_SSRF_PATCH_TARGET, return_value=True), patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await deliver_webhook(
            url="https://example.com/webhook",
            event_type="test.event",
            payload={},
            tenant_id="t1",
        )

    assert result is False
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_signature_header_present():
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch(_SSRF_PATCH_TARGET, return_value=True), patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await deliver_webhook(
            url="https://example.com/hook",
            event_type="test",
            payload={"key": "val"},
            tenant_id="tid",
        )

    call_kwargs = mock_client.post.call_args
    headers = call_kwargs.kwargs.get("headers", {})
    assert "X-LaunchLens-Signature" in headers
    assert headers["X-LaunchLens-Signature"].startswith("sha256=")
    assert headers["X-LaunchLens-Event"] == "test"


@pytest.mark.asyncio
async def test_ssrf_blocks_private_ips():
    """SSRF protection: deliver_webhook must reject URLs that resolve to private IPs."""
    # Mock DNS resolution to return a private IP
    with patch("launchlens.services.webhook_delivery.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 0, "", ("127.0.0.1", 0))]
        assert _is_url_safe("https://evil.example.com/webhook") is False

        mock_dns.return_value = [(2, 1, 0, "", ("10.0.0.1", 0))]
        assert _is_url_safe("https://internal.example.com/webhook") is False

        mock_dns.return_value = [(2, 1, 0, "", ("169.254.169.254", 0))]
        assert _is_url_safe("https://metadata.example.com/webhook") is False


@pytest.mark.asyncio
async def test_ssrf_allows_public_ips():
    """SSRF protection: deliver_webhook must allow URLs that resolve to public IPs."""
    with patch("launchlens.services.webhook_delivery.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 0, "", ("93.184.216.34", 0))]
        assert _is_url_safe("https://example.com/webhook") is True


@pytest.mark.asyncio
async def test_ssrf_rejects_non_http_schemes():
    """SSRF protection: reject non-HTTP(S) schemes."""
    assert _is_url_safe("ftp://example.com/file") is False
    assert _is_url_safe("file:///etc/passwd") is False


@pytest.mark.asyncio
async def test_ssrf_blocked_url_returns_false():
    """deliver_webhook returns False immediately for SSRF-blocked URLs."""
    with patch("launchlens.services.webhook_delivery._is_url_safe", return_value=False):
        result = await deliver_webhook(
            url="https://127.0.0.1/webhook",
            event_type="test",
            payload={},
            tenant_id="t1",
        )
    assert result is False
