"""
Google Cloud Vision provider.

Uses the REST API directly (not the google-cloud-vision SDK) to keep
the dependency footprint minimal.

Endpoint: POST https://vision.googleapis.com/v1/images:annotate
"""
import httpx
from launchlens.config import settings
from .base import VisionLabel, VisionProvider

_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


class GoogleVisionProvider(VisionProvider):
    def __init__(self, api_key: str = None):
        self._api_key = api_key or settings.google_vision_api_key

    async def analyze(self, image_url: str) -> list[VisionLabel]:
        payload = {
            "requests": [{
                "image": {"source": {"imageUri": image_url}},
                "features": [{"type": "LABEL_DETECTION", "maxResults": 20}],
            }]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _ENDPOINT,
                params={"key": self._api_key},
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()

        data = response.json()
        annotations = (
            data.get("responses", [{}])[0].get("labelAnnotations", [])
        )
        return [
            VisionLabel(
                name=ann["description"],
                confidence=ann["score"],
                category="general",
            )
            for ann in annotations
        ]
