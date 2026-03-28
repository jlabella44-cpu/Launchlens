# tests/test_monitoring/test_metrics.py
import asyncio
from unittest.mock import patch, MagicMock
import pytest


def test_emit_metric_calls_cloudwatch():
    from launchlens.monitoring.metrics import emit_metric
    mock_client = MagicMock()
    with patch("launchlens.monitoring.metrics._get_cloudwatch_client", return_value=mock_client):
        with patch("launchlens.monitoring.metrics.settings") as mock_settings:
            mock_settings.environment = "production"
            emit_metric("RequestCount", 1, unit="Count", dimensions={"endpoint": "/health"})
            mock_client.put_metric_data.assert_called_once()
            call_args = mock_client.put_metric_data.call_args[1]
            assert call_args["Namespace"] == "LaunchLens"
            metric = call_args["MetricData"][0]
            assert metric["MetricName"] == "RequestCount"
            assert metric["Value"] == 1


def test_emit_metric_noop_in_development():
    from launchlens.monitoring.metrics import emit_metric
    with patch("launchlens.monitoring.metrics.settings") as mock_settings:
        mock_settings.environment = "development"
        with patch("launchlens.monitoring.metrics._get_cloudwatch_client") as mock_cw:
            emit_metric("RequestCount", 1)
            mock_cw.assert_not_called()


@pytest.mark.asyncio
async def test_time_metric_decorator():
    from launchlens.monitoring.metrics import time_metric

    @time_metric("TestDuration")
    async def slow_function():
        await asyncio.sleep(0.01)
        return "done"

    with patch("launchlens.monitoring.metrics.emit_metric") as mock_emit:
        result = await slow_function()
        assert result == "done"
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "TestDuration"
        assert call_args[0][1] >= 10  # at least 10ms
