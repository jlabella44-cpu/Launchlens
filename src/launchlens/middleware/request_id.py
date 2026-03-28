"""
Request ID middleware.

Assigns a unique ID to every request, adds it to response headers,
and makes it available via request.state.request_id for structured logging.
"""
import logging
import uuid

from fastapi import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    async def __call__(self, request: Request, call_next) -> Response:
        # Use client-provided ID or generate one
        request_id = request.headers.get(_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        # Inject into log context for this request
        old_factory = logging.getLogRecordFactory()

        def factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            record.tenant_id = getattr(request.state, "tenant_id", None)
            return record

        logging.setLogRecordFactory(factory)

        try:
            response = await call_next(request)
        finally:
            logging.setLogRecordFactory(old_factory)

        response.headers[_HEADER] = request_id
        return response
