from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from launchlens.services.reso_adapter import RESOAdapter

BASE_URL = "https://reso.example.com/api"
API_KEY = "test-api-key"


def _ok_response(json_data=None, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status_code=500):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=resp
        )
    )
    return resp


@pytest.mark.asyncio
async def test_list_properties_sends_get():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(
        return_value=_ok_response({"value": [{"id": "1"}]})
    )

    adapter = RESOAdapter(BASE_URL, API_KEY, client=mock_client)
    result = await adapter.list_properties()

    assert result == [{"id": "1"}]
    mock_client.get.assert_called_once_with(
        f"{BASE_URL}/Property",
        params=None,
        headers={"Authorization": f"Bearer {API_KEY}"},
    )


@pytest.mark.asyncio
async def test_get_property_sends_get_with_id():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(
        return_value=_ok_response({"ListingId": "P-42", "beds": 3})
    )

    adapter = RESOAdapter(BASE_URL, API_KEY, client=mock_client)
    result = await adapter.get_property("P-42")

    assert result == {"ListingId": "P-42", "beds": 3}
    mock_client.get.assert_called_once_with(
        f"{BASE_URL}/Property('P-42')",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )


@pytest.mark.asyncio
async def test_submit_photos_sends_post():
    urls = ["https://img.example.com/1.jpg", "https://img.example.com/2.jpg"]
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(
        return_value=_ok_response({"status": "accepted"})
    )

    adapter = RESOAdapter(BASE_URL, API_KEY, client=mock_client)
    result = await adapter.submit_photos("P-99", urls)

    assert result == {"status": "accepted"}
    mock_client.post.assert_called_once_with(
        f"{BASE_URL}/Property('P-99')/Media",
        json=urls,
        headers={"Authorization": f"Bearer {API_KEY}"},
    )


@pytest.mark.asyncio
async def test_list_properties_passes_filters():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(
        return_value=_ok_response({"value": []})
    )

    adapter = RESOAdapter(BASE_URL, API_KEY, client=mock_client)
    filters = {"$filter": "City eq 'Austin'", "$top": "10"}
    await adapter.list_properties(filters=filters)

    _, kwargs = mock_client.get.call_args
    assert kwargs["params"] == filters


@pytest.mark.asyncio
async def test_raises_on_http_error():
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=_error_response(500))

    adapter = RESOAdapter(BASE_URL, API_KEY, client=mock_client)
    with pytest.raises(RuntimeError, match="500"):
        await adapter.list_properties()
