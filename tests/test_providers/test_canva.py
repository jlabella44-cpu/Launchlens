# tests/test_providers/test_canva.py
"""Tests for CanvaTemplateProvider — Canva Connect autofill + export flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from listingjet.providers.canva import CanvaTemplateProvider as CanvaProvider

SAMPLE_DATA = {
    "address": {"street": "123 Oak St", "city": "Austin", "state": "TX", "zip": "78701"},
    "metadata": {"beds": 3, "baths": 2, "sqft": 1800, "price": 450000},
    "description": "Stunning modern home",
    "hero_image_url": "https://example.com/hero.jpg",
    "agent_name": "Jane Doe",
    "brokerage_name": "Acme Realty",
    "primary_color": "#2563EB",
}


def _make_autofill_response(job_id: str = "af_1") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"job": {"id": job_id}}
    resp.raise_for_status = MagicMock()
    return resp


def _make_poll_response(status: str, result: dict | None = None) -> MagicMock:
    resp = MagicMock()
    job = {"status": status}
    if result:
        job["result"] = result
    resp.json.return_value = {"job": job}
    resp.raise_for_status = MagicMock()
    return resp


def _make_export_response(job_id: str = "ex_1") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"job": {"id": job_id}}
    resp.raise_for_status = MagicMock()
    return resp


def _make_pdf_response(content: bytes = b"%PDF-fake") -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_render_calls_autofill_then_export():
    """Full flow with hero image: upload asset, autofill template, export PDF."""
    # Hero asset upload POST response
    upload_resp = MagicMock()
    upload_resp.json.return_value = {"job": {"id": "upload_1"}}
    upload_resp.raise_for_status = MagicMock()

    autofill_resp = _make_autofill_response("af_1")
    export_resp = _make_export_response("ex_1")

    upload_poll = _make_poll_response("success", {"asset_id": "asset_abc"})
    autofill_poll = _make_poll_response("success", {"design_id": "design_abc"})
    export_poll = _make_poll_response("success", {"url": "https://canva.com/export/flyer.pdf"})
    pdf_resp = _make_pdf_response(b"%PDF-rendered")

    mock_client = AsyncMock()
    # POSTs: asset-upload, autofill, export
    mock_client.post = AsyncMock(side_effect=[upload_resp, autofill_resp, export_resp])
    # GETs: upload poll, autofill poll, export poll, PDF download
    mock_client.get = AsyncMock(side_effect=[upload_poll, autofill_poll, export_poll, pdf_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("listingjet.providers.canva.httpx.AsyncClient", return_value=mock_client):
        provider = CanvaProvider(api_key="test_key")
        result = await provider.render(template_id="tmpl_1", data=SAMPLE_DATA)

    assert result == b"%PDF-rendered"
    # 3 POSTs: asset-upload + autofill + export
    assert mock_client.post.call_count == 3
    # 4 GETs: upload poll + autofill poll + export poll + PDF download
    assert mock_client.get.call_count == 4


@pytest.mark.asyncio
async def test_render_without_hero_image_skips_upload():
    """When no hero_image_url is provided, asset upload is skipped."""
    data = {**SAMPLE_DATA, "hero_image_url": None}

    autofill_resp = _make_autofill_response()
    export_resp = _make_export_response()
    autofill_poll = _make_poll_response("success", {"design_id": "d1"})
    export_poll = _make_poll_response("success", {"url": "https://canva.com/out.pdf"})
    pdf_resp = _make_pdf_response()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[autofill_resp, export_resp])
    mock_client.get = AsyncMock(side_effect=[autofill_poll, export_poll, pdf_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("listingjet.providers.canva.httpx.AsyncClient", return_value=mock_client):
        provider = CanvaProvider(api_key="tok")
        result = await provider.render(template_id="tmpl_1", data=data)

    assert result == b"%PDF-fake"
    # Only autofill + export posts, no asset-upload post
    assert mock_client.post.call_count == 2


@pytest.mark.asyncio
async def test_render_sends_auth_header():
    """Canva API calls include the Bearer token in the Authorization header."""
    autofill_resp = _make_autofill_response()
    export_resp = _make_export_response()
    autofill_poll = _make_poll_response("success", {"design_id": "d1"})
    export_poll = _make_poll_response("success", {"url": "https://canva.com/out.pdf"})
    pdf_resp = _make_pdf_response()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[autofill_resp, export_resp])
    mock_client.get = AsyncMock(side_effect=[autofill_poll, export_poll, pdf_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("listingjet.providers.canva.httpx.AsyncClient", return_value=mock_client):
        provider = CanvaProvider(api_key="secret_key")
        data_no_hero = {**SAMPLE_DATA, "hero_image_url": None}
        await provider.render(template_id="tmpl_1", data=data_no_hero)

    # Check that the autofill POST was called with the Bearer header
    first_post_call = mock_client.post.call_args_list[0]
    headers_arg = first_post_call.kwargs.get("headers") or first_post_call[1].get("headers")
    assert headers_arg["Authorization"] == "Bearer secret_key"


@pytest.mark.asyncio
async def test_render_hero_upload_failure_still_renders():
    """If hero asset upload fails, render continues without the asset."""
    # Upload response that raises an error
    upload_resp = MagicMock()
    upload_resp.raise_for_status.side_effect = Exception("upload failed")

    autofill_resp = _make_autofill_response()
    export_resp = _make_export_response()
    autofill_poll = _make_poll_response("success", {"design_id": "d1"})
    export_poll = _make_poll_response("success", {"url": "https://canva.com/out.pdf"})
    pdf_resp = _make_pdf_response(b"%PDF-ok")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[upload_resp, autofill_resp, export_resp])
    mock_client.get = AsyncMock(side_effect=[autofill_poll, export_poll, pdf_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("listingjet.providers.canva.httpx.AsyncClient", return_value=mock_client):
        provider = CanvaProvider(api_key="tok")
        result = await provider.render(template_id="tmpl_1", data=SAMPLE_DATA)

    assert result == b"%PDF-ok"


@pytest.mark.asyncio
async def test_constructor_stores_api_key_and_llm():
    """Constructor accepts api_key and optional llm_provider."""
    mock_llm = MagicMock()
    provider = CanvaProvider(api_key="my_key", llm_provider=mock_llm)
    assert provider._api_key == "my_key"
    assert provider._llm is mock_llm
