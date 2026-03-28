# tests/test_monitoring/test_health.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(async_client: AsyncClient):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


@pytest.mark.asyncio
async def test_deep_health_returns_component_status(async_client: AsyncClient):
    resp = await async_client.get("/health/deep")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "database" in data
    assert "redis" in data
    assert "temporal" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_deep_health_database_ok(async_client: AsyncClient):
    """Test DB should be reachable via the test conftest setup."""
    resp = await async_client.get("/health/deep")
    data = resp.json()
    assert data["database"] == "ok"
