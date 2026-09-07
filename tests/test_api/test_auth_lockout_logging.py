import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_lockout_redis_failure_is_logged(async_client: AsyncClient, caplog):
    broken = MagicMock()
    broken.get.side_effect = ConnectionError("redis down")
    broken.pipeline.side_effect = ConnectionError("redis down")
    with patch("listingjet.api.auth._get_lockout_redis", return_value=broken):
        with caplog.at_level(logging.ERROR, logger="listingjet.api.auth"):
            resp = await async_client.post("/auth/login", json={
                "email": f"nobody-{uuid.uuid4()}@example.com", "password": "Wrong1!",
            })
    assert resp.status_code == 401  # login still fails open on the lockout check
    assert any("auth.lockout_backend_error" in r.message for r in caplog.records)
