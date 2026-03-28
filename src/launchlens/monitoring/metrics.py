"""
CloudWatch custom metrics helpers.

Namespace: LaunchLens
"""

from __future__ import annotations

import functools
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Lazy-initialized CloudWatch client
_cw_client = None


def _get_cw_client():
    global _cw_client
    if _cw_client is None:
        try:
            import boto3
            from launchlens.config import settings
            _cw_client = boto3.client("cloudwatch", region_name=settings.aws_region)
        except Exception:
            logger.warning("cloudwatch_client_init_failed", exc_info=True)
            return None
    return _cw_client


def emit_metric(
    name: str,
    value: float,
    unit: str = "Count",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit a single CloudWatch metric data point."""
    client = _get_cw_client()
    if client is None:
        return

    metric_data: dict[str, Any] = {
        "MetricName": name,
        "Value": value,
        "Unit": unit,
    }
    if dimensions:
        metric_data["Dimensions"] = [
            {"Name": k, "Value": v} for k, v in dimensions.items()
        ]

    try:
        client.put_metric_data(
            Namespace="LaunchLens",
            MetricData=[metric_data],
        )
    except Exception:
        logger.warning("cloudwatch_emit_failed", metric=name, exc_info=True)


def time_metric(stage: str):
    """Decorator that emits PipelineStageDuration for an async function."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return await fn(*args, **kwargs)
            finally:
                elapsed = time.monotonic() - start
                emit_metric(
                    "PipelineStageDuration",
                    value=elapsed,
                    unit="Seconds",
                    dimensions={"stage": stage},
                )
        return wrapper
    return decorator
