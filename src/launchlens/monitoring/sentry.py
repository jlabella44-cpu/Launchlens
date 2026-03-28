"""
Sentry SDK initialization with FastAPI integration.
"""

import os

import structlog

logger = structlog.get_logger(__name__)


def init_sentry(dsn: str, environment: str = "production") -> None:
    """Initialize Sentry error tracking. No-op if DSN is empty."""
    if not dsn:
        logger.info("sentry_disabled", reason="no DSN configured")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=os.environ.get("GIT_SHA", "unknown"),
            traces_sample_rate=0.0,  # No performance tracing at beta
            sample_rate=1.0,  # Capture all errors at beta scale
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
            ],
        )
        logger.info("sentry_initialized", environment=environment)
    except Exception:
        logger.warning("sentry_init_failed", exc_info=True)
