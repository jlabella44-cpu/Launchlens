# tests/test_monitoring/test_metrics.py
import asyncio
from unittest.mock import MagicMock, patch

import pytest


def test_emit_metric_calls_cloudwatch():
    from listingjet.monitoring.metrics import emit_metric
    mock_client = MagicMock()
    with patch("listingjet.monitoring.metrics._get_cloudwatch_client", return_value=mock_client):
        with patch("listingjet.monitoring.metrics.settings") as mock_settings:
            mock_settings.app_env = "production"
            mock_settings.cloudwatch_enabled = True
            emit_metric("RequestCount", 1, unit="Count", dimensions={"endpoint": "/health"})
            mock_client.put_metric_data.assert_called_once()
            call_args = mock_client.put_metric_data.call_args[1]
            assert call_args["Namespace"] == "ListingJet"
            metric = call_args["MetricData"][0]
            assert metric["MetricName"] == "RequestCount"
            assert metric["Value"] == 1


def test_emit_metric_noop_in_development():
    from listingjet.monitoring.metrics import emit_metric
    with patch("listingjet.monitoring.metrics.settings") as mock_settings:
        mock_settings.app_env = "development"
        mock_settings.cloudwatch_enabled = True  # even when enabled, dev noops
        with patch("listingjet.monitoring.metrics._get_cloudwatch_client") as mock_cw:
            emit_metric("RequestCount", 1)
            mock_cw.assert_not_called()


def test_emit_metric_noop_when_cloudwatch_disabled():
    """In non-dev environments, cloudwatch_enabled=False (the default for
    non-AWS deploys) must skip emitting and avoid creating a client."""
    from listingjet.monitoring.metrics import emit_metric
    with patch("listingjet.monitoring.metrics.settings") as mock_settings:
        mock_settings.app_env = "production"
        mock_settings.cloudwatch_enabled = False
        with patch("listingjet.monitoring.metrics._get_cloudwatch_client") as mock_cw:
            emit_metric("RequestCount", 1)
            mock_cw.assert_not_called()


@pytest.mark.asyncio
async def test_time_metric_decorator():
    from listingjet.monitoring.metrics import time_metric

    @time_metric("TestDuration")
    async def slow_function():
        await asyncio.sleep(0.05)
        return "done"

    with patch("listingjet.monitoring.metrics.emit_metric") as mock_emit:
        result = await slow_function()
        assert result == "done"
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "TestDuration"
        # 50ms sleep — assert >=30ms to allow headroom for Windows clock resolution.
        assert call_args[0][1] >= 30
