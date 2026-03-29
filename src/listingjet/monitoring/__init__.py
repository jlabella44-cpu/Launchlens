"""Monitoring package — initializes all observability components."""

import logging

from fastapi import FastAPI

from listingjet.config import settings
from listingjet.monitoring.middleware import RequestMetricsMiddleware
from listingjet.monitoring.sentry import init_sentry
from listingjet.telemetry import init_tracing

logger = logging.getLogger(__name__)


def init_monitoring(app: FastAPI) -> None:
    """Initialize all monitoring: Sentry, request metrics middleware."""
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=settings.git_sha,
    )
    init_tracing()

    app.middleware("http")(RequestMetricsMiddleware())

    logger.info("Monitoring initialized")
