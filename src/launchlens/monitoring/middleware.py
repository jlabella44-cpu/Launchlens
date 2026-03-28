"""
Request metrics middleware — emits latency, count, and error metrics per endpoint.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .metrics import emit_metric


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Tracks request latency, count, and errors as CloudWatch metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        endpoint = f"{request.method} {request.url.path}"
        start = time.monotonic()

        response = await call_next(request)

        latency_ms = (time.monotonic() - start) * 1000
        status = str(response.status_code)

        emit_metric("RequestLatency", latency_ms, unit="Milliseconds", dimensions={"endpoint": endpoint})
        emit_metric("RequestCount", 1, dimensions={"endpoint": endpoint, "status_code": status})

        if response.status_code >= 500:
            emit_metric("ErrorCount", 1, dimensions={"endpoint": endpoint})

        return response
