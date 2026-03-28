import json
from unittest.mock import AsyncMock, patch

import pytest

from launchlens.services.webhook_delivery import deliver_webhook


@pytest.mark.asyncio
async def test_successful_delivery():
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
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

    with patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
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
    with patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
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

    with patch("launchlens.services.webhook_delivery.httpx.AsyncClient") as mock_client_cls:
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
