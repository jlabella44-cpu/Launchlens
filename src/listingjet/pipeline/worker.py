"""Standalone worker: python -m listingjet.pipeline.worker
Same loops as the in-process worker in main.py, for a dedicated worker service."""
import asyncio
import logging
import signal
from pathlib import Path

from listingjet.config import settings
from listingjet.database import admin_session
from listingjet.logging_config import setup_logging
from listingjet.monitoring.sentry import init_sentry
from listingjet.pipeline.runner import periodic_loop, worker_loop

logger = logging.getLogger(__name__)
HEARTBEAT_FILE = Path("/tmp/worker-heartbeat")


async def _heartbeat(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            HEARTBEAT_FILE.touch()
        except OSError:
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    # Same structured/JSON logging setup the API applies at import time —
    # without it this process logs with the bare root handler.
    setup_logging(app_env=settings.app_env, log_level=settings.log_level)
    init_sentry(dsn=settings.sentry_dsn, environment=settings.app_env, release=settings.git_sha)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows
            pass
    logger.info("pipeline worker starting concurrency=%s", settings.worker_concurrency)
    await asyncio.gather(
        worker_loop(admin_session, stop=stop, concurrency=settings.worker_concurrency,
                    poll_interval_s=settings.worker_poll_interval_s),
        periodic_loop(admin_session, stop=stop),
        _heartbeat(stop),
    )


if __name__ == "__main__":
    asyncio.run(main())
