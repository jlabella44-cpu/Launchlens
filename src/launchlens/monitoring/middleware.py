"""Request metrics middleware — records latency, count, and errors per endpoint."""

import logging
import time

from fastapi import Request
from starlette.responses import Response

from launchlens.monitoring.metrics import emit_metric

logger = logging.getLogger(__name__)


class RequestMetricsMiddleware:
    """Emits CloudWatch metrics for every request: latency, count, errors."""

    async def __call__(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        endpoint = request.url.path
        status = str(response.status_code)

        emit_metric(
            "RequestLatency",
            duration_ms,
            unit="Milliseconds",
            dimensions={"endpoint": endpoint},
        )
        emit_metric(
            "RequestCount",
            1,
            unit="Count",
            dimensions={"endpoint": endpoint, "status_code": status},
        )

        if response.status_code >= 400:
            emit_metric(
                "ErrorCount",
                1,
                unit="Count",
                dimensions={"endpoint": endpoint},
            )

        return response
