import fakeredis
import pytest

from launchlens.services.rate_limiter import RateLimiter


@pytest.fixture
def limiter():
    client = fakeredis.FakeRedis()
    return RateLimiter(redis_client=client, key_prefix="test")


def test_acquire_within_limit_returns_true(limiter):
    for _ in range(3):
        assert limiter.acquire(key="google_vision", cost=1) is True


def test_acquire_exceeds_capacity_returns_false(limiter):
    small = RateLimiter(
        redis_client=fakeredis.FakeRedis(),
        key_prefix="test",
        capacity=2,
        refill_rate=0,
    )
    assert small.acquire(key="google_vision", cost=1) is True
    assert small.acquire(key="google_vision", cost=1) is True
    assert small.acquire(key="google_vision", cost=1) is False


def test_acquire_cost_greater_than_one(limiter):
    small = RateLimiter(
        redis_client=fakeredis.FakeRedis(),
        key_prefix="test",
        capacity=5,
        refill_rate=0,
    )
    assert small.acquire(key="gpt4v", cost=3) is True
    assert small.acquire(key="gpt4v", cost=3) is False  # only 2 tokens left


def test_different_keys_are_independent(limiter):
    small = RateLimiter(
        redis_client=fakeredis.FakeRedis(),
        key_prefix="test",
        capacity=1,
        refill_rate=0,
    )
    assert small.acquire(key="google_vision", cost=1) is True
    assert small.acquire(key="google_vision", cost=1) is False
    assert small.acquire(key="gpt4v", cost=1) is True
