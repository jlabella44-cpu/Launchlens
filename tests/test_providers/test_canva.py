# tests/test_providers/test_canva.py
"""Tests for CanvaProvider — two-step Claude design spec + Canva render flow."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launchlens.providers.canva import CanvaProvider


def _make_mock_llm(design_json: dict) -> MagicMock:
    mock = MagicMock()
    mock.complete = AsyncMock(return_value=json.dumps(design_json))
    return mock


SAMPLE_DESIGN = {
    "template_id": "listing-flyer-v1",
    "background_color": "#FFFFFF",
    "text_blocks": [
        {"id": "headline", "text": "Stunning Modern Home", "font_size": 36, "color": "#111111"},
        {"id": "address", "text": "123 Oak St, Austin TX", "font_size": 18, "color": "#555555"},
        {"id": "details", "text": "3 bd | 2 ba | 1,800 sqft", "font_size": 14, "color": "#555555"},
    ],
    "image_url": "https://example.com/hero.jpg",
}


@pytest.mark.asyncio
async def test_render_flyer_calls_claude_then_canva():
    """Full two-step flow: Claude generates JSON, Canva renders and returns URL."""
    mock_llm = _make_mock_llm(SAMPLE_DESIGN)

    mock_create_resp = MagicMock()
    mock_create_resp.json.return_value = {"design": {"id": "design_abc123"}}
    mock_create_resp.raise_for_status = MagicMock()

    mock_export_resp = MagicMock()
    mock_export_resp.json.return_value = {"export": {"url": "https://canva.com/export/flyer.pdf"}}
    mock_export_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_create_resp, mock_export_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("launchlens.providers.canva.httpx.AsyncClient", return_value=mock_client):
        provider = CanvaProvider(api_token="test_token", llm_provider=mock_llm)
        url = await provider.render_flyer(
            listing_details={"beds": 3, "baths": 2, "price": 450000},
            hero_image_url="https://example.com/hero.jpg",
        )

    assert url == "https://canva.com/export/flyer.pdf"
    mock_llm.complete.assert_called_once()
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_design_spec_strips_markdown():
    """Markdown fences around JSON are stripped before parsing."""
    design = SAMPLE_DESIGN.copy()
    raw_with_fences = f"```json\n{json.dumps(design)}\n```"
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value=raw_with_fences)

    provider = CanvaProvider(api_token="tok", llm_provider=mock_llm)
    result = await provider._generate_design_spec(
        listing_details={"beds": 3},
        hero_image_url="",
        brand_color="#2563EB",
    )
    assert result["template_id"] == "listing-flyer-v1"
    assert "text_blocks" in result


@pytest.mark.asyncio
async def test_generate_design_spec_requires_llm():
    """Raises RuntimeError if no LLM provider is configured."""
    provider = CanvaProvider(api_token="tok", llm_provider=None)
    with pytest.raises(RuntimeError, match="LLM provider required"):
        await provider._generate_design_spec({}, "", "#000")


@pytest.mark.asyncio
async def test_render_with_canva_sends_auth_header():
    """Canva API calls include the Bearer token in the Authorization header."""
    captured_headers: list[dict] = []

    mock_create_resp = MagicMock()
    mock_create_resp.json.return_value = {"design": {"id": "d_xyz"}}
    mock_create_resp.raise_for_status = MagicMock()

    mock_export_resp = MagicMock()
    mock_export_resp.json.return_value = {"export": {"url": "https://canva.com/out.pdf"}}
    mock_export_resp.raise_for_status = MagicMock()

    async def _post(url, headers=None, json=None):
        captured_headers.append(dict(headers or {}))
        return mock_create_resp if "designs" in url else mock_export_resp

    mock_client = AsyncMock()
    mock_client.post = _post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("launchlens.providers.canva.httpx.AsyncClient", return_value=mock_client):
        provider = CanvaProvider(api_token="secret_token")
        await provider._render_with_canva(SAMPLE_DESIGN)

    assert captured_headers[0]["Authorization"] == "Bearer secret_token"


@pytest.mark.asyncio
async def test_render_flyer_passes_brand_color_to_llm():
    """Brand color is forwarded to the LLM via context."""
    mock_llm = MagicMock()
    captured_kwargs: dict = {}

    async def _complete(prompt, context=None):
        captured_kwargs["context"] = context
        return json.dumps(SAMPLE_DESIGN)

    mock_llm.complete = _complete

    mock_create_resp = MagicMock()
    mock_create_resp.json.return_value = {"design": {"id": "d1"}}
    mock_create_resp.raise_for_status = MagicMock()

    mock_export_resp = MagicMock()
    mock_export_resp.json.return_value = {"export": {"url": "https://canva.com/out.pdf"}}
    mock_export_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_create_resp, mock_export_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("launchlens.providers.canva.httpx.AsyncClient", return_value=mock_client):
        provider = CanvaProvider(api_token="tok", llm_provider=mock_llm)
        await provider.render_flyer(
            listing_details={"beds": 4},
            brand_color="#FF5733",
        )

    assert captured_kwargs["context"]["brand_color"] == "#FF5733"
