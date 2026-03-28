# tests/test_monitoring/test_middleware.py
import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_metrics_middleware_emits_metrics(async_client: AsyncClient):
    """Middleware should emit RequestLatency and RequestCount metrics."""
    with patch("launchlens.monitoring.middleware.emit_metric") as mock_emit:
        resp = await async_client.get("/health")
        assert resp.status_code == 200

        metric_names = [call.args[0] for call in mock_emit.call_args_list]
        assert "RequestLatency" in metric_names
        assert "RequestCount" in metric_names


@pytest.mark.asyncio
async def test_request_metrics_tracks_errors(async_client: AsyncClient):
    """Middleware should emit ErrorCount for 4xx/5xx responses."""
    with patch("launchlens.monitoring.middleware.emit_metric") as mock_emit:
        resp = await async_client.get("/nonexistent-route-xyz")

        error_calls = [c for c in mock_emit.call_args_list if c.args[0] == "ErrorCount"]
        if resp.status_code >= 400:
            assert len(error_calls) >= 1
