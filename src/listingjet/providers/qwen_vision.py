# src/listingjet/providers/qwen_vision.py
"""
Qwen 3.6 Plus vision provider — used for Tier 2 aesthetic re-ranking.

Uses Alibaba Cloud DashScope's OpenAI-compatible endpoint.
Sends image URLs in the messages array (native multimodal vision).
Expects the model to return a JSON object with a "labels" array.

Concurrency: Semaphore(max_concurrent) prevents more than N simultaneous
calls to avoid rate limits. Default is 5.
"""
import asyncio
import json

import httpx

from listingjet.config import settings
from listingjet.services.metrics import record_provider_call

from .base import VisionLabel, VisionProvider

_DEFAULT_ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
_SYSTEM_PROMPT = (
    "You are a real estate photography analyst. "
    "Analyze the image and return a JSON object with a single key 'labels' "
    "containing an array of objects, each with 'name', 'confidence' (0.0-1.0), "
    "and 'category' (one of: shot_type, quality, feature, room) fields. "
    "Return only valid JSON, no markdown."
)


class QwenVisionProvider(VisionProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_concurrent: int = 5,
    ):
        self._api_key = api_key or settings.dashscope_api_key
        self._base_url = (base_url or settings.dashscope_base_url).rstrip("/")
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @property
    def _endpoint(self) -> str:
        return f"{self._base_url}/chat/completions"

    async def analyze(self, image_url: str) -> list[VisionLabel]:
        payload = {
            "model": "qwen3.6-plus",
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": "Analyze this real estate photo."},
                    ],
                },
            ],
            "max_tokens": 500,
        }
        try:
            async with self._semaphore:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self._endpoint,
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=payload,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Qwen returned unparseable JSON: {content!r}") from e
            record_provider_call("qwen_vision", True)
        except Exception:
            record_provider_call("qwen_vision", False)
            raise

        return [
            VisionLabel(
                name=item["name"],
                confidence=item["confidence"],
                category=item.get("category", "general"),
            )
            for item in data.get("labels", [])
        ]

    async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
        payload = {
            "model": "qwen3.6-plus",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            "max_tokens": 2000,
        }
        try:
            async with self._semaphore:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self._endpoint,
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=payload,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    result = response.json()["choices"][0]["message"]["content"]
            record_provider_call("qwen_vision", True)
            return result
        except Exception:
            record_provider_call("qwen_vision", False)
            raise
