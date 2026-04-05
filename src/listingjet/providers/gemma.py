# src/listingjet/providers/gemma.py
"""
Google Gemma 4 provider — cheap, high-volume LLM and vision tasks.

Gemma 4 is Apache 2.0 licensed and available via the Gemini API's
OpenAI-compatible endpoint. Cost-effective for bulk classification
(PhotoComplianceAgent, VisionAgent tier-1) and volume copy generation
(SocialContentAgent).

Default model: gemma-4-31b-it (dense flagship, 256K context).
"""
import asyncio
import json

import httpx

from listingjet.config import settings
from listingjet.services.metrics import record_provider_call

from .base import LLMProvider, VisionLabel, VisionProvider

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
_MODEL = "gemma-4-31b-it"
_DEFAULT_SYSTEM_PROMPT = (
    "You are an expert real estate copywriter. "
    "Write compelling, accurate, and legally compliant listing descriptions. "
    "Avoid Fair Housing Act violations. Be specific about features, never generic."
)
_VISION_SYSTEM_PROMPT = (
    "You are a real estate photography analyst. "
    "Analyze the image and return a JSON object with a single key 'labels' "
    "containing an array of objects, each with 'name', 'confidence' (0.0-1.0), "
    "and 'category' (one of: shot_type, quality, feature, room) fields. "
    "Return only valid JSON, no markdown."
)


class GemmaProvider(LLMProvider):
    """Gemma 4 LLM provider via Gemini API OpenAI-compatible endpoint."""

    def __init__(self, api_key: str | None = None, model: str = _MODEL):
        self._api_key = api_key or settings.gemini_api_key
        self._model = model
        self._endpoint = f"{_BASE_URL}/chat/completions"

    async def complete(
        self,
        prompt: str,
        context: dict,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        context_str = json.dumps(context, indent=2) if context else ""
        user_content = f"{prompt}\n\nContext:\n{context_str}" if context_str else prompt

        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt or _DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 1024,
        }
        if temperature is not None:
            payload["temperature"] = max(0.0, min(1.0, temperature))

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._endpoint,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                    timeout=60.0,
                )
                response.raise_for_status()
                result = response.json()["choices"][0]["message"]["content"]
            record_provider_call("gemma", True)
            return result
        except Exception:
            record_provider_call("gemma", False)
            raise


class GemmaVisionProvider(VisionProvider):
    """Gemma 4 multimodal vision provider (image input)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _MODEL,
        max_concurrent: int = 10,
    ):
        self._api_key = api_key or settings.gemini_api_key
        self._model = model
        self._endpoint = f"{_BASE_URL}/chat/completions"
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def analyze(self, image_url: str) -> list[VisionLabel]:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _VISION_SYSTEM_PROMPT},
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
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Gemma returned unparseable JSON: {content!r}") from e
            record_provider_call("gemma_vision", True)
        except Exception:
            record_provider_call("gemma_vision", False)
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
            "model": self._model,
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
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    result = response.json()["choices"][0]["message"]["content"]
            record_provider_call("gemma_vision", True)
            return result
        except Exception:
            record_provider_call("gemma_vision", False)
            raise
