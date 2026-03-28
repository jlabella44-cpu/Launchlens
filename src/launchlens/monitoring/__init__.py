"""
LaunchLens Monitoring — structlog logging, CloudWatch metrics, Sentry error tracking.

Call init_monitoring(app) during FastAPI lifespan to wire everything up.
"""

from fastapi import FastAPI

from launchlens.config import settings

from .logging import configure_structlog
from .middleware import RequestMetricsMiddleware
from .sentry import init_sentry


def init_monitoring(app: FastAPI) -> None:
    """Initialize all monitoring subsystems and attach middleware."""
    configure_structlog(environment=settings.environment)
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
    )
    app.add_middleware(RequestMetricsMiddleware)
