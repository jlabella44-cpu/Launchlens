# src/listingjet/services/rate_limiter.py
"""
Token bucket rate limiter backed by Redis.

Uses WATCH/MULTI/EXEC pipeline for atomic check-and-decrement.
Each provider key (e.g. "google_vision", "gpt4v") has its own bucket.

Usage:
    limiter = RateLimiter(redis_client=redis.from_url(settings.redis_url))
    if not limiter.acquire(key="google_vision", cost=1):
        raise RateLimitExceeded("google_vision")
"""
import time

import redis as redis_lib


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    def __init__(
        self,
        redis_client=None,
        key_prefix: str = "ratelimit",
        capacity: int = 10,
        refill_rate: float = 1.0,  # tokens per second
    ):
        if redis_client is None:
            from listingjet.config import settings
            redis_client = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        self._redis = redis_client
        self._prefix = key_prefix
        self._capacity = capacity
        self._refill_rate = refill_rate

    def acquire(self, key: str, cost: int = 1) -> bool:
        """Attempt to consume `cost` tokens. Returns True if allowed."""
        allowed, _ = self.acquire_with_remaining(key, cost)
        return allowed

    def acquire_with_remaining(self, key: str, cost: int = 1) -> tuple[bool, int]:
        """Attempt to consume tokens. Returns (allowed, remaining_tokens)."""
        bucket_key = f"{self._prefix}:{key}"
        now = time.time()

        with self._redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(bucket_key)
                    data = pipe.hgetall(bucket_key)

                    if data:
                        tokens = float(data.get(b"tokens", self._capacity))
                        last_refill = float(data.get(b"last_refill", now))
                    else:
                        tokens = float(self._capacity)
                        last_refill = now

                    elapsed = now - last_refill
                    tokens = min(
                        float(self._capacity),
                        tokens + elapsed * self._refill_rate,
                    )

                    allowed = tokens >= cost

                    pipe.multi()
                    new_tokens = (tokens - cost) if allowed else tokens
                    pipe.hset(bucket_key, mapping={
                        "tokens": new_tokens,
                        "last_refill": now,
                    })
                    pipe.expire(bucket_key, 3600)
                    pipe.execute()
                    return allowed, max(0, int(new_tokens))

                except redis_lib.WatchError:
                    # Another client modified the key; retry
                    continue
