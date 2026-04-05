# src/listingjet/providers/_retry.py
"""
Retry helper with exponential backoff for transient provider failures.

Used by provider classes that call external APIs over HTTP. Only retries
on network-level/5xx errors; 4xx responses are raised immediately so
misuse isn't masked.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retries(
    fn: Callable[[], Awaitable[T]],
    *,
    provider: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> T:
    """Run *fn*, retrying on transient network/5xx failures.

    Args:
        fn: Zero-arg async callable that performs the provider request.
        provider: Provider label used in log messages.
        max_attempts: Total tries including the first.
        base_delay: Seconds for the first backoff; doubles each retry.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except httpx.HTTPStatusError as exc:
            # Only retry on 5xx and 429
            status = exc.response.status_code
            if status < 500 and status != 429:
                raise
            last_exc = exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc

        if attempt == max_attempts:
            break
        delay = base_delay * (2 ** (attempt - 1))
        logger.warning(
            "provider %s failed (attempt %d/%d), retrying in %.1fs: %s",
            provider, attempt, max_attempts, delay, last_exc,
        )
        await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc
