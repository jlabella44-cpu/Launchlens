"""Monitoring package — initializes all observability components."""

import logging

from fastapi import FastAPI

from listingjet.config import settings
from listingjet.monitoring.sentry import init_sentry

logger = logging.getLogger(__name__)


def init_monitoring(app: FastAPI) -> None:
    """Initialize all monitoring: Sentry."""
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=settings.git_sha,
    )

    logger.info("Monitoring initialized")
