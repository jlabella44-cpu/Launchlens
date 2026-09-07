"""Regression for the Task 8 shutdown fix: lifespan shutdown must tolerate
`asyncio.CancelledError` (not just `asyncio.TimeoutError`) from the per-worker
`asyncio.wait_for` call, still cancel + await each worker task, and still
close the Redis client afterward.
"""
import asyncio

import pytest
from fastapi import FastAPI

from listingjet import main as main_module
from listingjet.pipeline import runner as runner_module


async def _sleep_forever(*args, **kwargs):
    await asyncio.Event().wait()


class _ExplodingOutboxPoller:
    """Stand-in for OutboxPoller that fails to start, exercising the same
    'outbox poller failed to start' branch main.py already handles — keeps
    this test from needing a real DB connection."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError("no DB in this unit test")


@pytest.mark.asyncio
async def test_lifespan_shutdown_tolerates_cancelled_error_and_closes_redis(monkeypatch):
    monkeypatch.setattr(main_module.settings, "worker_enabled", True)
    monkeypatch.setattr(main_module, "OutboxPoller", _ExplodingOutboxPoller)
    monkeypatch.setattr(runner_module, "worker_loop", _sleep_forever)
    monkeypatch.setattr(runner_module, "periodic_loop", _sleep_forever)

    import redis as redis_module

    closed = {"called": False}

    class _FakeRedis:
        def ping(self):
            return True

        def close(self):
            closed["called"] = True

    fake_redis = _FakeRedis()
    monkeypatch.setattr(redis_module, "from_url", lambda *a, **k: fake_redis)

    real_wait_for = asyncio.wait_for
    call_count = 0

    async def fake_wait_for(fut, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulates the surrounding shutdown itself being cancelled while
            # awaiting the first worker task — this is Fix 3's regression.
            raise asyncio.CancelledError()
        # Second call: exercise the pre-existing TimeoutError branch too,
        # with a tiny timeout since the stub tasks sleep forever.
        return await real_wait_for(fut, timeout=0.01)

    monkeypatch.setattr(main_module.asyncio, "wait_for", fake_wait_for)

    app = FastAPI()
    async with asyncio.timeout(5):
        async with main_module.lifespan(app):
            worker_tasks = [t for t in asyncio.all_tasks() if not t.done() and t is not asyncio.current_task()]
            assert len(worker_tasks) >= 2, "expected worker_loop + periodic_loop tasks to be running"

    # Every task the lifespan spawned for the worker/periodic loops must have
    # ended cancelled, not merely abandoned.
    for t in worker_tasks:
        assert t.cancelled(), f"expected task {t!r} to be cancelled after shutdown"

    assert closed["called"], "app.state.redis.close() must still run despite CancelledError"
    assert call_count >= 2, "expected both worker tasks' wait_for calls to be exercised"
