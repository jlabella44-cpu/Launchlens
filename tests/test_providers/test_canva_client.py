import pytest

from listingjet.providers.canva_client import CanvaClient, CanvaError


@pytest.mark.asyncio
async def test_create_autofill_posts_and_returns_job_id(httpx_mock):
    httpx_mock.add_response(method="POST", url="https://api.canva.com/rest/v1/autofills",
                            json={"job": {"id": "af_1", "status": "in_progress"}})
    async with CanvaClient(token="tok") as c:
        assert await c.create_autofill("tpl", {"x": {"type": "text", "text": "y"}}) == "af_1"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer tok"
    import json

    assert json.loads(req.read()) == {
        "brand_template_id": "tpl",
        "data": {"x": {"type": "text", "text": "y"}},
    }


@pytest.mark.asyncio
async def test_get_autofill_normalises_result(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/autofills/af_1",
                            json={"job": {"id": "af_1", "status": "success", "result": {"type": "create_design", "design": {"id": "d_9"}}}})
    async with CanvaClient(token="tok") as c:
        assert await c.get_autofill("af_1") == {"status": "success", "design_id": "d_9"}


@pytest.mark.asyncio
async def test_error_body_raises(httpx_mock):
    httpx_mock.add_response(method="POST", url="https://api.canva.com/rest/v1/exports", status_code=400,
                            json={"error": {"code": "bad", "message": "nope"}})
    async with CanvaClient(token="tok") as c:
        with pytest.raises(CanvaError) as exc:
            await c.create_export("d_9", {"type": "pdf"})
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_url_asset_upload_posts_and_returns_job_id(httpx_mock):
    httpx_mock.add_response(method="POST", url="https://api.canva.com/rest/v1/url-asset-uploads",
                            json={"job": {"id": "up_1", "status": "in_progress"}})
    async with CanvaClient(token="tok") as c:
        assert await c.create_url_asset_upload("hero_image", "https://example.com/x.jpg") == "up_1"


@pytest.mark.asyncio
async def test_get_url_asset_upload_normalises_result(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/url-asset-uploads/up_1",
                            json={"job": {"id": "up_1", "status": "success", "asset": {"id": "asset_abc"}}})
    async with CanvaClient(token="tok") as c:
        assert await c.get_url_asset_upload("up_1") == {"status": "success", "asset_id": "asset_abc"}


@pytest.mark.asyncio
async def test_get_url_asset_upload_absent_asset_is_none(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/url-asset-uploads/up_1",
                            json={"job": {"id": "up_1", "status": "in_progress"}})
    async with CanvaClient(token="tok") as c:
        assert await c.get_url_asset_upload("up_1") == {"status": "in_progress", "asset_id": None}


@pytest.mark.asyncio
async def test_create_export_posts_and_returns_job_id(httpx_mock):
    httpx_mock.add_response(method="POST", url="https://api.canva.com/rest/v1/exports",
                            json={"job": {"id": "ex_1", "status": "in_progress"}})
    async with CanvaClient(token="tok") as c:
        job_id = await c.create_export("d_9", {"type": "pdf"})
    assert job_id == "ex_1"
    req = httpx_mock.get_requests()[0]
    import json

    assert json.loads(req.read()) == {"design_id": "d_9", "format": {"type": "pdf"}}


@pytest.mark.asyncio
async def test_get_export_normalises_result(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/exports/ex_1",
                            json={"job": {"id": "ex_1", "status": "success", "urls": ["https://canva.com/out.pdf"]}})
    async with CanvaClient(token="tok") as c:
        assert await c.get_export("ex_1") == {"status": "success", "urls": ["https://canva.com/out.pdf"]}


@pytest.mark.asyncio
async def test_get_export_absent_urls_is_empty_list(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/exports/ex_1",
                            json={"job": {"id": "ex_1", "status": "in_progress"}})
    async with CanvaClient(token="tok") as c:
        assert await c.get_export("ex_1") == {"status": "in_progress", "urls": []}


@pytest.mark.asyncio
async def test_get_autofill_absent_design_is_none(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/autofills/af_1",
                            json={"job": {"id": "af_1", "status": "in_progress"}})
    async with CanvaClient(token="tok") as c:
        assert await c.get_autofill("af_1") == {"status": "in_progress", "design_id": None}


@pytest.mark.asyncio
async def test_download_returns_bytes(httpx_mock):
    httpx_mock.add_response(url="https://canva.com/export/flyer.pdf", content=b"%PDF-1.4 bytes")
    async with CanvaClient(token="tok") as c:
        assert await c.download("https://canva.com/export/flyer.pdf") == b"%PDF-1.4 bytes"


@pytest.mark.asyncio
async def test_download_does_not_leak_bearer_token_to_export_host(httpx_mock):
    httpx_mock.add_response(url="https://export-cdn.example.com/file.pdf", content=b"file-bytes")
    async with CanvaClient(token="tok") as c:
        assert await c.download("https://export-cdn.example.com/file.pdf") == b"file-bytes"
    req = httpx_mock.get_requests()[0]
    assert "authorization" not in {k.lower() for k in req.headers.keys()}


@pytest.mark.asyncio
async def test_download_error_raises_canva_error(httpx_mock):
    httpx_mock.add_response(url="https://export-cdn.example.com/file.pdf", status_code=403, content=b"forbidden")
    async with CanvaClient(token="tok") as c:
        with pytest.raises(CanvaError) as exc:
            await c.download("https://export-cdn.example.com/file.pdf")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_error_status_without_body_raises(httpx_mock):
    httpx_mock.add_response(url="https://api.canva.com/rest/v1/autofills/af_1", status_code=500, json={})
    async with CanvaClient(token="tok") as c:
        with pytest.raises(CanvaError) as exc:
            await c.get_autofill("af_1")
    assert exc.value.status_code == 500
