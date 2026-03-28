from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from launchlens.providers.canva import CanvaTemplateProvider


@pytest.mark.asyncio
async def test_canva_render_posts_to_api():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b"PDF-bytes"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    provider = CanvaTemplateProvider(api_key="test-key", client=mock_client)
    result = await provider.render("tmpl-1", {"title": "Open House"})

    assert result == b"PDF-bytes"
    mock_client.post.assert_called_once_with(
        "https://api.canva.com/v1/designs/tmpl-1/render",
        json={"title": "Open House"},
        headers={"Authorization": "Bearer test-key"},
    )


@pytest.mark.asyncio
async def test_canva_render_sends_auth_header():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b"ok"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    provider = CanvaTemplateProvider(api_key="secret-123", client=mock_client)
    await provider.render("tmpl-2", {})

    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret-123"


@pytest.mark.asyncio
async def test_canva_render_raises_on_http_error():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
    )

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    provider = CanvaTemplateProvider(api_key="key", client=mock_client)
    with pytest.raises(RuntimeError, match="500"):
        await provider.render("tmpl-3", {"bad": "data"})
