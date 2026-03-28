import pytest


@pytest.mark.asyncio
async def test_response_has_request_id(async_client):
    resp = await async_client.get("/health")
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) > 0


@pytest.mark.asyncio
async def test_client_provided_request_id_preserved(async_client):
    resp = await async_client.get("/health", headers={"X-Request-ID": "my-custom-id"})
    assert resp.headers["x-request-id"] == "my-custom-id"
