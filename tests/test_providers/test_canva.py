# tests/test_providers/test_canva.py
"""Tests for CanvaTemplateProvider — Canva Connect autofill + export flow.

Uses the generated Canva client API functions. Mocks are applied to the
generated module-level async functions rather than raw httpx calls.
"""
from http import HTTPStatus
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

# ---------------------------------------------------------------------------
# Helpers to build mock Response objects matching the generated client shape
# ---------------------------------------------------------------------------

_GEN = "listingjet.providers.canva"


def _ok_response(parsed):
    """Build a mock Response with status 200 and a parsed model."""
    resp = MagicMock()
    resp.status_code = HTTPStatus.OK
    resp.parsed = parsed
    return resp


def _make_autofill_create_parsed(job_id: str = "af_1"):
    """Mock CreateDesignAutofillJobResponse."""
    parsed = MagicMock()
    parsed.job.id = job_id
    return parsed


def _make_autofill_poll_parsed(status: str, design_id: str | None = None):
    """Mock GetDesignAutofillJobResponse."""
    parsed = MagicMock()
    parsed.job.status.value = status
    if design_id:
        parsed.job.result.design.id = design_id
    return parsed


def _make_export_create_parsed(job_id: str = "ex_1"):
    """Mock CreateDesignExportJobResponse."""
    parsed = MagicMock()
    parsed.job.id = job_id
    return parsed


def _make_export_poll_parsed(status: str, url: str | None = None):
    """Mock GetDesignExportJobResponse."""
    parsed = MagicMock()
    parsed.job.status.value = status
    if url:
        parsed.job.urls = [url]
    return parsed


def _make_upload_create_parsed(job_id: str = "upload_1"):
    """Mock CreateUrlAssetUploadJobResponse."""
    parsed = MagicMock()
    parsed.job.id = job_id
    return parsed


def _make_upload_poll_parsed(status: str, asset_id: str | None = None):
    """Mock GetUrlAssetUploadJobResponse."""
    parsed = MagicMock()
    parsed.job.status.value = status
    if asset_id:
        parsed.job.asset.id = asset_id
    return parsed


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_calls_autofill_then_export():
    """Full flow with hero image: upload asset, autofill template, export PDF."""
    # Set up mock returns for each generated API call
    mock_create_upload = AsyncMock(
        return_value=_ok_response(_make_upload_create_parsed("upload_1"))
    )
    mock_poll_upload = AsyncMock(
        return_value=_ok_response(_make_upload_poll_parsed("success", "asset_abc"))
    )
    mock_create_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_create_parsed("af_1"))
    )
    mock_poll_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_poll_parsed("success", "design_abc"))
    )
    mock_create_export = AsyncMock(
        return_value=_ok_response(_make_export_create_parsed("ex_1"))
    )
    mock_poll_export = AsyncMock(
        return_value=_ok_response(_make_export_poll_parsed("success", "https://canva.com/export/flyer.pdf"))
    )

    # Mock the PDF download via raw httpx
    mock_http_client = AsyncMock()
    mock_http_resp = MagicMock()
    mock_http_resp.content = b"%PDF-rendered"
    mock_http_resp.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_http_resp)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(f"{_GEN}.create_url_asset_upload_job.asyncio_detailed", mock_create_upload),
        patch(f"{_GEN}.get_url_asset_upload_job.asyncio_detailed", mock_poll_upload),
        patch(f"{_GEN}.create_design_autofill_job.asyncio_detailed", mock_create_autofill),
        patch(f"{_GEN}.get_design_autofill_job.asyncio_detailed", mock_poll_autofill),
        patch(f"{_GEN}.create_design_export_job.asyncio_detailed", mock_create_export),
        patch(f"{_GEN}.get_design_export_job.asyncio_detailed", mock_poll_export),
        patch(f"{_GEN}.httpx.AsyncClient", return_value=mock_http_client),
        patch(f"{_GEN}.AuthenticatedClient") as mock_auth_cls,
    ):
        mock_client_inst = MagicMock()
        mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
        mock_client_inst.__aexit__ = AsyncMock(return_value=None)
        mock_auth_cls.return_value = mock_client_inst

        provider = CanvaProvider(api_key="test_key")
        result = await provider.render(template_id="tmpl_1", data=SAMPLE_DATA)

    assert result == b"%PDF-rendered"
    # Verify all API stages were called
    mock_create_upload.assert_called_once()
    mock_poll_upload.assert_called_once()
    mock_create_autofill.assert_called_once()
    mock_poll_autofill.assert_called_once()
    mock_create_export.assert_called_once()
    mock_poll_export.assert_called_once()


@pytest.mark.asyncio
async def test_render_without_hero_image_skips_upload():
    """When no hero_image_url is provided, asset upload is skipped."""
    data = {**SAMPLE_DATA, "hero_image_url": None}

    mock_create_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_create_parsed("af_1"))
    )
    mock_poll_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_poll_parsed("success", "d1"))
    )
    mock_create_export = AsyncMock(
        return_value=_ok_response(_make_export_create_parsed("ex_1"))
    )
    mock_poll_export = AsyncMock(
        return_value=_ok_response(_make_export_poll_parsed("success", "https://canva.com/out.pdf"))
    )
    mock_create_upload = AsyncMock()

    mock_http_client = AsyncMock()
    mock_http_resp = MagicMock()
    mock_http_resp.content = b"%PDF-fake"
    mock_http_resp.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_http_resp)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(f"{_GEN}.create_url_asset_upload_job.asyncio_detailed", mock_create_upload),
        patch(f"{_GEN}.create_design_autofill_job.asyncio_detailed", mock_create_autofill),
        patch(f"{_GEN}.get_design_autofill_job.asyncio_detailed", mock_poll_autofill),
        patch(f"{_GEN}.create_design_export_job.asyncio_detailed", mock_create_export),
        patch(f"{_GEN}.get_design_export_job.asyncio_detailed", mock_poll_export),
        patch(f"{_GEN}.httpx.AsyncClient", return_value=mock_http_client),
        patch(f"{_GEN}.AuthenticatedClient") as mock_auth_cls,
    ):
        mock_client_inst = MagicMock()
        mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
        mock_client_inst.__aexit__ = AsyncMock(return_value=None)
        mock_auth_cls.return_value = mock_client_inst

        provider = CanvaProvider(api_key="tok")
        result = await provider.render(template_id="tmpl_1", data=data)

    assert result == b"%PDF-fake"
    # Upload should NOT have been called
    mock_create_upload.assert_not_called()
    # Autofill + export should still run
    mock_create_autofill.assert_called_once()
    mock_create_export.assert_called_once()


@pytest.mark.asyncio
async def test_render_passes_token_to_authenticated_client():
    """AuthenticatedClient is constructed with the correct token."""
    mock_create_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_create_parsed())
    )
    mock_poll_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_poll_parsed("success", "d1"))
    )
    mock_create_export = AsyncMock(
        return_value=_ok_response(_make_export_create_parsed())
    )
    mock_poll_export = AsyncMock(
        return_value=_ok_response(_make_export_poll_parsed("success", "https://canva.com/out.pdf"))
    )

    mock_http_client = AsyncMock()
    mock_http_resp = MagicMock()
    mock_http_resp.content = b"%PDF-ok"
    mock_http_resp.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_http_resp)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(f"{_GEN}.create_design_autofill_job.asyncio_detailed", mock_create_autofill),
        patch(f"{_GEN}.get_design_autofill_job.asyncio_detailed", mock_poll_autofill),
        patch(f"{_GEN}.create_design_export_job.asyncio_detailed", mock_create_export),
        patch(f"{_GEN}.get_design_export_job.asyncio_detailed", mock_poll_export),
        patch(f"{_GEN}.httpx.AsyncClient", return_value=mock_http_client),
        patch(f"{_GEN}.AuthenticatedClient") as mock_auth_cls,
    ):
        mock_client_inst = MagicMock()
        mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
        mock_client_inst.__aexit__ = AsyncMock(return_value=None)
        mock_auth_cls.return_value = mock_client_inst

        data_no_hero = {**SAMPLE_DATA, "hero_image_url": None}
        provider = CanvaProvider(api_key="secret_key")
        await provider.render(template_id="tmpl_1", data=data_no_hero)

    # Verify AuthenticatedClient was constructed with the right token
    mock_auth_cls.assert_called_once()
    call_kwargs = mock_auth_cls.call_args
    assert call_kwargs.kwargs.get("token") == "secret_key"


@pytest.mark.asyncio
async def test_render_hero_upload_failure_still_renders():
    """If hero asset upload fails, render continues without the asset."""
    mock_create_upload = AsyncMock(side_effect=Exception("upload failed"))

    mock_create_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_create_parsed())
    )
    mock_poll_autofill = AsyncMock(
        return_value=_ok_response(_make_autofill_poll_parsed("success", "d1"))
    )
    mock_create_export = AsyncMock(
        return_value=_ok_response(_make_export_create_parsed())
    )
    mock_poll_export = AsyncMock(
        return_value=_ok_response(_make_export_poll_parsed("success", "https://canva.com/out.pdf"))
    )

    mock_http_client = AsyncMock()
    mock_http_resp = MagicMock()
    mock_http_resp.content = b"%PDF-ok"
    mock_http_resp.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_http_resp)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(f"{_GEN}.create_url_asset_upload_job.asyncio_detailed", mock_create_upload),
        patch(f"{_GEN}.create_design_autofill_job.asyncio_detailed", mock_create_autofill),
        patch(f"{_GEN}.get_design_autofill_job.asyncio_detailed", mock_poll_autofill),
        patch(f"{_GEN}.create_design_export_job.asyncio_detailed", mock_create_export),
        patch(f"{_GEN}.get_design_export_job.asyncio_detailed", mock_poll_export),
        patch(f"{_GEN}.httpx.AsyncClient", return_value=mock_http_client),
        patch(f"{_GEN}.AuthenticatedClient") as mock_auth_cls,
    ):
        mock_client_inst = MagicMock()
        mock_client_inst.__aenter__ = AsyncMock(return_value=mock_client_inst)
        mock_client_inst.__aexit__ = AsyncMock(return_value=None)
        mock_auth_cls.return_value = mock_client_inst

        provider = CanvaProvider(api_key="tok")
        result = await provider.render(template_id="tmpl_1", data=SAMPLE_DATA)

    assert result == b"%PDF-ok"
    # Upload was attempted (hero_image_url was set) but failed gracefully
    mock_create_upload.assert_called_once()


@pytest.mark.asyncio
async def test_constructor_stores_api_key_and_llm():
    """Constructor accepts api_key and optional llm_provider."""
    mock_llm = MagicMock()
    provider = CanvaProvider(api_key="my_key", llm_provider=mock_llm)
    assert provider._api_key == "my_key"
    assert provider._llm is mock_llm
