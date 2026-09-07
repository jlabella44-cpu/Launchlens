"""Runway image-to-video client (Dev API).

Thin async wrapper around Runway's `/v1/image_to_video` + `/v1/tasks/{id}`
endpoints. Uses raw httpx, mirroring the house style established by
`providers/openai_images.py` — no `runwayml` SDK dependency.

Request/response facts verified against the official Runway Python SDK:
- base `https://api.dev.runwayml.com`
- headers: `Authorization: Bearer <key>`, `X-Runway-Version: 2024-11-06`
- `POST /v1/image_to_video` JSON body:
    {"model", "promptImage", "promptText", "duration", "ratio"}
  plus `"audio": <bool>` only when the caller passes `audio` (veo3.1_fast
  supports it; gen4_turbo does not) -> `{"id": "..."}`
- `GET /v1/tasks/{id}` ->
    {"status": "PENDING"|"THROTTLED"|"RUNNING"|"SUCCEEDED"|"FAILED"|"CANCELLED",
     "output": [url, ...], "failure": str?, "failureCode": str?, "progress": float?}
  Output URLs expire within 24-48h — callers must download promptly.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from listingjet.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.dev.runwayml.com"
_VERSION = "2024-11-06"

_DOWNLOAD_TIMEOUT = 120.0
_MAX_RETRIES = 3
_RETRY_BACKOFF_S = (2.0, 4.0, 8.0)
_MAX_POLL_INTERVAL_S = 20.0
_POLL_GROWTH = 1.5

_TERMINAL_FAILURE_STATUSES = {"FAILED", "CANCELLED"}


class RunwayError(Exception):
    """Raised when a Runway API call fails or a task never resolves."""


class RunwayTaskFailed(RunwayError):
    """Raised when a Runway task resolves to FAILED or CANCELLED."""

    def __init__(self, message: str, *, task_id: str, failure_code: str | None = None):
        super().__init__(message)
        self.task_id = task_id
        self.failure_code = failure_code


class RunwayClient:
    """Talks to Runway's Dev API for image-to-video generation."""

    provider_name = "runway"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = _BASE_URL,
        version: str = _VERSION,
        timeout_s: float = 60.0,
    ):
        self._api_key = api_key or settings.runway_api_key
        self._base_url = base_url.rstrip("/")
        self._version = version
        self._timeout_s = timeout_s
        self._client = httpx.AsyncClient(timeout=timeout_s)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-Runway-Version": self._version,
        }

    async def image_to_video(
        self,
        image_url: str,
        prompt: str,
        *,
        model: str,
        duration: int,
        ratio: str = "1280:720",
        audio: bool | None = None,
    ) -> str:
        """Submit an image-to-video task. Returns the task id."""
        body: dict = {
            "model": model,
            "promptImage": image_url,
            "promptText": prompt,
            "duration": duration,
            "ratio": ratio,
        }
        if audio is not None:
            body["audio"] = audio

        resp = await self._request(
            "POST", f"{self._base_url}/v1/image_to_video", json=body,
        )
        data = resp.json()
        try:
            return data["id"]
        except KeyError as exc:
            raise RunwayError(f"Unexpected response shape: {data}") from exc

    async def get_task(self, task_id: str) -> dict:
        """Fetch the current state of a task."""
        resp = await self._request("GET", f"{self._base_url}/v1/tasks/{task_id}")
        return resp.json()

    async def wait(
        self,
        task_id: str,
        *,
        timeout_s: float = 900.0,
        poll_s: float = 5.0,
    ) -> list[str]:
        """Poll a task until it resolves. Returns the output URLs on success.

        Raises RunwayTaskFailed on FAILED/CANCELLED, RunwayError on timeout.
        """
        elapsed = 0.0
        interval = poll_s
        while True:
            task = await self.get_task(task_id)
            status = task.get("status")

            if status == "SUCCEEDED":
                return task.get("output") or []
            if status in _TERMINAL_FAILURE_STATUSES:
                raise RunwayTaskFailed(
                    task.get("failure") or f"Runway task {task_id} resolved {status}",
                    task_id=task_id,
                    failure_code=task.get("failureCode"),
                )

            if elapsed >= timeout_s:
                raise RunwayError(
                    f"Runway task {task_id} did not resolve within {timeout_s}s "
                    f"(last status: {status})"
                )

            await asyncio.sleep(interval)
            elapsed += interval
            interval = min(interval * _POLL_GROWTH, _MAX_POLL_INTERVAL_S)

    async def download(self, url: str) -> bytes:
        """Download rendered video bytes from an (expiring) output URL."""
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, *, json: dict | None = None) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await self._client.request(method, url, headers=self._headers(), json=json)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt >= _MAX_RETRIES:
                    raise RunwayError(f"Runway request error: {exc}") from exc
                await asyncio.sleep(_RETRY_BACKOFF_S[attempt])
                continue

            if resp.status_code < 400:
                return resp

            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = RunwayError(
                    f"Runway {method} {url} returned {resp.status_code}: {resp.text[:500]}"
                )
                if attempt >= _MAX_RETRIES:
                    raise last_exc
                await asyncio.sleep(_RETRY_BACKOFF_S[attempt])
                continue

            # 4xx: no retry
            raise RunwayError(
                f"Runway {method} {url} returned {resp.status_code}: {resp.text[:500]}"
            )

        # Unreachable, but keeps type-checkers happy.
        raise last_exc or RunwayError("Runway request failed")
