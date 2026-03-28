# src/launchlens/providers/canva.py
"""
Canva template provider — renders flyer / social assets via the Canva API.
"""
import httpx

from .base import TemplateProvider


class CanvaTemplateProvider(TemplateProvider):
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.canva.com/v1",
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient()

    async def render(self, template_id: str, data: dict) -> bytes:
        """POST design data to Canva and return the rendered bytes."""
        url = f"{self._base_url}/designs/{template_id}/render"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = await self._client.post(url, json=data, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Canva render failed with status {exc.response.status_code}"
            ) from exc
        return response.content
