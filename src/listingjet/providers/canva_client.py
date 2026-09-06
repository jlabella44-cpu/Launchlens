# src/listingjet/providers/canva_client.py
"""Thin async HTTP client for the Canva Connect API.

Replaces the vendored/generated Canva SDK with direct httpx calls against
the handful of endpoints ListingJet actually uses: URL asset uploads,
brand-template autofills, and design exports.
"""
from __future__ import annotations

import httpx


class CanvaError(Exception):
    """Raised when the Canva API returns a non-2xx response or an error body."""

    def __init__(self, status_code: int, body):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Canva API error {status_code}: {body}")


class CanvaClient:
    """Minimal async client for the Canva Connect REST API."""

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.canva.com/rest",
        timeout: float = 60.0,
    ):
        self._token = token
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    async def __aenter__(self) -> "CanvaClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc_info):
        await self._client.__aexit__(*exc_info)

    async def _post(self, path: str, body: dict) -> dict:
        resp = await self._client.post(path, json=body)
        return self._parse(resp)

    async def _get(self, path: str) -> dict:
        resp = await self._client.get(path)
        return self._parse(resp)

    @staticmethod
    def _parse(resp: httpx.Response) -> dict:
        try:
            payload = resp.json()
        except ValueError:
            payload = None
        if resp.is_error or (isinstance(payload, dict) and "error" in payload):
            raise CanvaError(resp.status_code, payload)
        return payload

    async def create_url_asset_upload(self, name: str, url: str) -> str:
        body = await self._post("/v1/url-asset-uploads", {"name": name, "url": url})
        return body["job"]["id"]

    async def get_url_asset_upload(self, job_id: str) -> dict:
        body = await self._get(f"/v1/url-asset-uploads/{job_id}")
        job = body["job"]
        return {
            "status": job.get("status"),
            "asset_id": job.get("asset", {}).get("id") if job.get("asset") else None,
        }

    async def create_autofill(self, brand_template_id: str, data: dict) -> str:
        body = await self._post(
            "/v1/autofills",
            {"brand_template_id": brand_template_id, "data": data},
        )
        return body["job"]["id"]

    async def get_autofill(self, job_id: str) -> dict:
        body = await self._get(f"/v1/autofills/{job_id}")
        job = body["job"]
        result = job.get("result") or {}
        design = result.get("design") or {}
        return {
            "status": job.get("status"),
            "design_id": design.get("id"),
        }

    async def create_export(self, design_id: str, fmt: dict) -> str:
        body = await self._post(
            "/v1/exports",
            {"design_id": design_id, "format": fmt},
        )
        return body["job"]["id"]

    async def get_export(self, job_id: str) -> dict:
        body = await self._get(f"/v1/exports/{job_id}")
        job = body["job"]
        return {
            "status": job.get("status"),
            "urls": job.get("urls", []),
        }

    async def download(self, url: str) -> bytes:
        # Export URLs are typically presigned S3/CDN links, not Canva API
        # endpoints — reusing self._client would leak our Canva bearer token
        # to that host (and presigned URLs often reject extra auth headers).
        # Use a bare, unauthenticated client for this one call.
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url)
            if resp.is_error:
                raise CanvaError(resp.status_code, resp.content)
            return resp.content
