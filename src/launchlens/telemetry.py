"""
OpenTelemetry tracing setup for LaunchLens.

Provides:
- ``init_tracing()``: configure the global TracerProvider + OTLP exporter
- ``agent_span()``: async context manager that wraps an agent's execute() in a span
"""

import logging
from contextlib import asynccontextmanager

from launchlens.config import settings

logger = logging.getLogger(__name__)

_tracer = None


def init_tracing() -> None:
    """Set up the OpenTelemetry TracerProvider with OTLP gRPC exporter.

    No-op when OTEL_EXPORTER_OTLP_ENDPOINT is not configured or in development
    without an explicit endpoint.
    """
    global _tracer

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": "launchlens",
            "service.version": settings.git_sha or "dev",
            "deployment.environment": settings.app_env,
        })
        provider = TracerProvider(resource=resource)

        # Only attach an exporter if we have an endpoint
        otlp_endpoint = _get_otlp_endpoint()
        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OpenTelemetry tracing enabled (endpoint=%s)", otlp_endpoint)
        else:
            logger.debug("No OTLP endpoint configured — tracing spans are local only")

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("launchlens")
    except ImportError:
        logger.warning("opentelemetry-sdk not installed — tracing disabled")


def _get_otlp_endpoint() -> str:
    """Return the OTLP endpoint from config or env, empty string if unset."""
    import os

    return getattr(settings, "otel_exporter_endpoint", "") or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", ""
    )


def get_tracer():
    """Return the global tracer, initialising lazily if needed."""
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace

            _tracer = trace.get_tracer("launchlens")
        except ImportError:
            return None
    return _tracer


@asynccontextmanager
async def agent_span(agent_name: str, listing_id: str, tenant_id: str):
    """Wrap agent execution in an OpenTelemetry span.

    Yields the span (or ``None`` if tracing is unavailable) so callers can
    attach custom attributes::

        async with agent_span("ingestion", lid, tid) as span:
            ...
            if span:
                span.set_attribute("result.count", 42)
    """
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry.trace import StatusCode

    with tracer.start_as_current_span(f"agent.{agent_name}") as span:
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("listing.id", str(listing_id))
        span.set_attribute("tenant.id", str(tenant_id))
        try:
            yield span
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
        else:
            span.set_status(StatusCode.OK)
