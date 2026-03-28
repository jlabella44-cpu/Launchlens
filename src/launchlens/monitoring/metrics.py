"""CloudWatch custom metrics helpers."""

import functools
import logging
import time

import boto3

from launchlens.config import settings

logger = logging.getLogger(__name__)

_cloudwatch_client = None


def _get_cloudwatch_client():
    global _cloudwatch_client
    if _cloudwatch_client is None:
        _cloudwatch_client = boto3.client("cloudwatch", region_name=settings.aws_region)
    return _cloudwatch_client


def emit_metric(
    name: str,
    value: float,
    unit: str = "None",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit a CloudWatch custom metric. No-op in development."""
    if settings.environment == "development":
        return

    try:
        cw_dimensions = [{"Name": k, "Value": v} for k, v in (dimensions or {}).items()]
        _get_cloudwatch_client().put_metric_data(
            Namespace="LaunchLens",
            MetricData=[
                {
                    "MetricName": name,
                    "Value": value,
                    "Unit": unit,
                    "Dimensions": cw_dimensions,
                }
            ],
        )
    except Exception:
        logger.exception("Failed to emit metric %s", name)


def time_metric(metric_name: str, dimensions: dict[str, str] | None = None):
    """Decorator that times an async function and emits the duration as a metric."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.monotonic() - start) * 1000
                emit_metric(metric_name, duration_ms, unit="Milliseconds", dimensions=dimensions)
        return wrapper
    return decorator
