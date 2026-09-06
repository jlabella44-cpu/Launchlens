# tests/test_providers/test_canva.py
"""Tests for CanvaTemplateProvider — Canva Connect autofill + export flow.

Mocks are applied to `CanvaClient` (the thin httpx client) rather than
raw HTTP calls or a generated SDK.
"""
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

_GEN = "listingjet.providers.canva"


def _make_client_mock(
    *,
    upload_job_id="upload_1",
    upload_status="success",
    upload_asset_id="asset_abc",
    upload_side_effect=None,
    autofill_job_id="af_1",
    autofill_status="success",
    autofill_design_id="design_abc",
    export_job_id="ex_1",
    export_status="success",
    export_urls=None,
    pdf_bytes=b"%PDF-rendered",
):
    """Build an AsyncMock CanvaClient instance with normalised return shapes."""
    export_urls = export_urls if export_urls is not None else ["https://canva.com/export/flyer.pdf"]

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    if upload_side_effect is not None:
        client.create_url_asset_upload = AsyncMock(side_effect=upload_side_effect)
    else:
        client.create_url_asset_upload = AsyncMock(return_value=upload_job_id)
    client.get_url_asset_upload = AsyncMock(
        return_value={"status": upload_status, "asset_id": upload_asset_id}
    )

    client.create_autofill = AsyncMock(return_value=autofill_job_id)
    client.get_autofill = AsyncMock(
        return_value={"status": autofill_status, "design_id": autofill_design_id}
    )

    client.create_export = AsyncMock(return_value=export_job_id)
    client.get_export = AsyncMock(
        return_value={"status": export_status, "urls": export_urls}
    )

    client.download = AsyncMock(return_value=pdf_bytes)

    return client


@pytest.mark.asyncio
async def test_render_calls_autofill_then_export():
    """Full flow with hero image: upload asset, autofill template, export PDF."""
    mock_client = _make_client_mock(pdf_bytes=b"%PDF-rendered")

    with patch(f"{_GEN}.CanvaClient", return_value=mock_client):
        provider = CanvaProvider(api_key="test_key")
        result = await provider.render(template_id="tmpl_1", data=SAMPLE_DATA)

    assert result == b"%PDF-rendered"
    # Verify all API stages were called
    mock_client.create_url_asset_upload.assert_called_once()
    mock_client.get_url_asset_upload.assert_called_once()
    mock_client.create_autofill.assert_called_once()
    mock_client.get_autofill.assert_called_once()
    mock_client.create_export.assert_called_once()
    mock_client.get_export.assert_called_once()
    mock_client.download.assert_called_once()


@pytest.mark.asyncio
async def test_render_without_hero_image_skips_upload():
    """When no hero_image_url is provided, asset upload is skipped."""
    data = {**SAMPLE_DATA, "hero_image_url": None}
    mock_client = _make_client_mock(pdf_bytes=b"%PDF-fake")

    with patch(f"{_GEN}.CanvaClient", return_value=mock_client):
        provider = CanvaProvider(api_key="tok")
        result = await provider.render(template_id="tmpl_1", data=data)

    assert result == b"%PDF-fake"
    mock_client.create_url_asset_upload.assert_not_called()
    mock_client.create_autofill.assert_called_once()
    mock_client.create_export.assert_called_once()


@pytest.mark.asyncio
async def test_render_passes_token_to_canva_client():
    """CanvaClient is constructed with the correct token."""
    mock_client = _make_client_mock(pdf_bytes=b"%PDF-ok")

    with patch(f"{_GEN}.CanvaClient", return_value=mock_client) as mock_client_cls:
        data_no_hero = {**SAMPLE_DATA, "hero_image_url": None}
        provider = CanvaProvider(api_key="secret_key")
        await provider.render(template_id="tmpl_1", data=data_no_hero)

    mock_client_cls.assert_called_once()
    call_kwargs = mock_client_cls.call_args
    assert call_kwargs.kwargs.get("token") == "secret_key"


@pytest.mark.asyncio
async def test_render_hero_upload_failure_still_renders():
    """If hero asset upload fails, render continues without the asset."""
    mock_client = _make_client_mock(
        upload_side_effect=Exception("upload failed"), pdf_bytes=b"%PDF-ok"
    )

    with patch(f"{_GEN}.CanvaClient", return_value=mock_client):
        provider = CanvaProvider(api_key="tok")
        result = await provider.render(template_id="tmpl_1", data=SAMPLE_DATA)

    assert result == b"%PDF-ok"
    mock_client.create_url_asset_upload.assert_called_once()


@pytest.mark.asyncio
async def test_constructor_stores_api_key_and_llm():
    """Constructor accepts api_key and optional llm_provider."""
    mock_llm = MagicMock()
    provider = CanvaProvider(api_key="my_key", llm_provider=mock_llm)
    assert provider._api_key == "my_key"
    assert provider._llm is mock_llm
