"""Monitoring package — initializes all observability components."""

import logging

from fastapi import FastAPI

from launchlens.config import settings
from launchlens.monitoring.middleware import RequestMetricsMiddleware
from launchlens.monitoring.sentry import init_sentry

logger = logging.getLogger(__name__)


def init_monitoring(app: FastAPI) -> None:
    """Initialize all monitoring: Sentry, request metrics middleware."""
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.git_sha,
    )

    app.middleware("http")(RequestMetricsMiddleware())

    logger.info("Monitoring initialized")
