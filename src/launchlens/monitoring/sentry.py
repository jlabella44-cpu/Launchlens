"""Sentry SDK initialization."""

import logging

logger = logging.getLogger(__name__)


def init_sentry(dsn: str = "", environment: str = "development", release: str = "") -> None:
    """Initialize Sentry SDK. No-op if DSN is not configured."""
    if not dsn:
        logger.debug("Sentry DSN not configured — skipping Sentry init")
        return

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release or None,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized (environment=%s)", environment)
    except ImportError:
        logger.warning("sentry-sdk not installed — Sentry disabled")
