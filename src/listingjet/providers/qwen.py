# src/listingjet/providers/qwen.py
"""
Alibaba Qwen provider — used for long-context LLM and multimodal tasks.

Qwen 3.6-Plus features a 1M-token context window and strong agentic coding
capabilities, making it well-suited for long-context agents (FloorplanAgent,
CMAReportAgent, LearningAgent, MicrositeAgent).

Uses the DashScope OpenAI-compatible endpoint so we can reuse the same
request shape as OpenAI-based providers.
"""
import asyncio
import json

import httpx

from listingjet.config import settings
from listingjet.services.metrics import record_provider_call, record_token_usage

from ._retry import with_retries
from .base import LLMProvider, VisionLabel, VisionProvider

_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
_MODEL = "qwen3.6-plus"
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


async def _post(
    endpoint: str, api_key: str, payload: dict, provider_label: str
) -> dict:
    async def _do() -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()

    return await with_retries(_do, provider=provider_label)


def _extract_usage(body: dict) -> tuple[int, int]:
    usage = body.get("usage") or {}
    return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))


class QwenProvider(LLMProvider):
    """Qwen 3.6-Plus LLM provider via DashScope OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _MODEL,
        enable_cache: bool | None = None,
    ):
        self._api_key = api_key or settings.qwen_api_key
        self._model = model
        self._endpoint = f"{_BASE_URL}/chat/completions"
        self._enable_cache = (
            enable_cache if enable_cache is not None else settings.qwen_enable_cache
        )

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
        if self._enable_cache:
            # DashScope context-cache hint; the system message is cached between calls
            payload["enable_cache"] = True

        try:
            body = await _post(self._endpoint, self._api_key, payload, "qwen")
            result = body["choices"][0]["message"]["content"]
            input_tokens, output_tokens = _extract_usage(body)
            record_provider_call("qwen", True)
            if input_tokens or output_tokens:
                record_token_usage("qwen", input_tokens, output_tokens)
            return result
        except Exception:
            record_provider_call("qwen", False)
            raise


class QwenVisionProvider(VisionProvider):
    """Qwen 3.6-Plus multimodal vision provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _MODEL,
        max_concurrent: int = 5,
    ):
        self._api_key = api_key or settings.qwen_api_key
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
                body = await _post(self._endpoint, self._api_key, payload, "qwen_vision")
            content = body["choices"][0]["message"]["content"]
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Qwen returned unparseable JSON: {content!r}") from e
            input_tokens, output_tokens = _extract_usage(body)
            record_provider_call("qwen_vision", True)
            if input_tokens or output_tokens:
                record_token_usage("qwen_vision", input_tokens, output_tokens)
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
                body = await _post(self._endpoint, self._api_key, payload, "qwen_vision")
            result = body["choices"][0]["message"]["content"]
            input_tokens, output_tokens = _extract_usage(body)
            record_provider_call("qwen_vision", True)
            if input_tokens or output_tokens:
                record_token_usage("qwen_vision", input_tokens, output_tokens)
            return result
        except Exception:
            record_provider_call("qwen_vision", False)
            raise
