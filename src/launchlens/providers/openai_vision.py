# src/launchlens/providers/openai_vision.py
"""
OpenAI GPT-4V provider — used for Tier 2 aesthetic re-ranking.

Sends the image URL in the messages array (vision feature).
Expects the model to return a JSON object with a "labels" array.

Concurrency: Semaphore(max_concurrent) prevents more than N simultaneous
calls to avoid OpenAI rate limits. Default is 5.
"""
import asyncio
import json

import httpx

from launchlens.config import settings

from .base import VisionLabel, VisionProvider

_ENDPOINT = "https://api.openai.com/v1/chat/completions"
_SYSTEM_PROMPT = (
    "You are a real estate photography analyst. "
    "Analyze the image and return a JSON object with a single key 'labels' "
    "containing an array of objects, each with 'name', 'confidence' (0.0-1.0), "
    "and 'category' (one of: shot_type, quality, feature, room) fields. "
    "Return only valid JSON, no markdown."
)


class OpenAIVisionProvider(VisionProvider):
    def __init__(self, api_key: str = None, max_concurrent: int = 5):
        self._api_key = api_key or settings.openai_api_key
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def analyze(self, image_url: str) -> list[VisionLabel]:
        payload = {
            "model": "gpt-4o",
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
        async with self._semaphore:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    _ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"GPT-4V returned unparseable JSON: {content!r}") from e

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
            "model": "gpt-4o",
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
        async with self._semaphore:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    _ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
