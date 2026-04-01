"""
Shared async retry utilities with exponential backoff and jitter.
"""
import asyncio
import functools
import logging
import random
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, BaseException, float], Awaitable[None]] | None = None,
):
    """Async retry decorator with exponential backoff.

    Usage::

        @async_retry(max_retries=3, retry_on=(httpx.HTTPError, TimeoutError))
        async def call_api():
            ...
    """

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except retry_on as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    if jitter:
                        delay += delay * random.uniform(0, 0.25)
                    logger.warning(
                        "retry.attempt fn=%s attempt=%d/%d error=%s delay=%.2fs",
                        fn.__qualname__,
                        attempt,
                        max_retries,
                        exc,
                        delay,
                    )
                    if on_retry is not None:
                        await on_retry(attempt, exc, delay)
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


@asynccontextmanager
async def retry_context(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
):
    """Context-manager retry for inline use.

    Usage::

        async with retry_context(max_retries=3) as attempt:
            result = await some_call()

    ``attempt`` is a dict with ``{"number": int}`` tracking the current try.
    """
    attempt: dict[str, int] = {"number": 0}
    last_exc: BaseException | None = None
    for try_num in range(1, max_retries + 1):
        attempt["number"] = try_num
        try:
            yield attempt
            return  # success
        except retry_on as exc:
            last_exc = exc
            if try_num == max_retries:
                break
            delay = min(base_delay * (exponential_base ** (try_num - 1)), max_delay)
            if jitter:
                delay += delay * random.uniform(0, 0.25)
            logger.warning(
                "retry_context attempt=%d/%d error=%s delay=%.2fs",
                try_num,
                max_retries,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]
