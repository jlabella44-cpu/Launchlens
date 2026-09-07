"""Claude client: text, structured JSON, and image analysis on the anthropic 1.x SDK.

Model IDs come from settings (claude_fast_model for per-photo work,
claude_quality_model for copy and floorplans). Current models reject
sampling parameters, so temperature is never sent; tone lives in the system prompt.
"""
from __future__ import annotations

import json
import logging

import anthropic
from pydantic import BaseModel

from listingjet.config import settings
from listingjet.services.metrics import record_provider_call, record_token_usage

from .base import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert real estate copywriter. Write compelling, accurate, and legally "
    "compliant listing descriptions. Avoid Fair Housing Act violations. Be specific about "
    "features, never generic."
)


class ProviderOutputError(RuntimeError):
    """The model returned no usable output (refusal, empty, or schema mismatch)."""


class ClaudeClient:
    def __init__(self, api_key: str | None = None):
        self._client = anthropic.AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)

    async def _parse(self, *, messages, schema, system, model, max_tokens, agent):
        model = model or settings.claude_quality_model
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages, "output_format": schema}
        if system:
            kwargs["system"] = system
        try:
            resp = await self._client.messages.parse(**kwargs)
        except Exception:
            record_provider_call("claude", False)
            raise
        usage = getattr(resp, "usage", None)
        if usage is not None:
            record_token_usage(model, usage.input_tokens, usage.output_tokens, agent)
        if getattr(resp, "parsed_output", None) is None:
            record_provider_call("claude", False)
            raise ProviderOutputError(f"no structured output (stop_reason={getattr(resp, 'stop_reason', None)!r})")
        record_provider_call("claude", True)
        return resp.parsed_output

    async def complete_json(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        agent: str | None = None,
    ) -> BaseModel:
        return await self._parse(
            messages=[{"role": "user", "content": prompt}],
            schema=schema,
            system=system,
            model=model,
            max_tokens=max_tokens,
            agent=agent,
        )

    async def analyze_images(
        self,
        image_urls: list[str],
        prompt: str,
        schema: type[BaseModel],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        agent: str | None = None,
    ) -> BaseModel:
        if not image_urls:
            raise ValueError("image_urls must be non-empty")
        content = [{"type": "image", "source": {"type": "url", "url": u}} for u in image_urls]
        content.append({"type": "text", "text": prompt})
        return await self._parse(
            messages=[{"role": "user", "content": content}],
            schema=schema,
            system=system,
            model=model,
            max_tokens=max_tokens,
            agent=agent,
        )

    async def complete_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        agent: str | None = None,
    ) -> str:
        model = model or settings.claude_quality_model
        kwargs = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        try:
            resp = await self._client.messages.create(**kwargs)
        except Exception:
            record_provider_call("claude", False)
            raise
        usage = getattr(resp, "usage", None)
        if usage is not None:
            record_token_usage(model, usage.input_tokens, usage.output_tokens, agent)
        if getattr(resp, "stop_reason", None) == "refusal":
            record_provider_call("claude", False)
            raise ProviderOutputError("model refused")
        record_provider_call("claude", True)
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


class ClaudeProvider(LLMProvider):
    """Legacy text interface used by content/social agents until Phase 5. `temperature` is ignored."""

    def __init__(self, api_key: str | None = None, client: ClaudeClient | None = None):
        self._client = client or ClaudeClient(api_key=api_key)

    async def complete(
        self,
        prompt: str,
        context: dict,
        temperature: float | None = None,
        system_prompt: str | None = None,
        agent: str | None = None,
    ) -> str:
        context_str = json.dumps(context, indent=2, default=str) if context else ""
        user = f"{prompt}\n\nContext:\n{context_str}" if context_str else prompt
        return await self._client.complete_text(
            user, system=system_prompt or DEFAULT_SYSTEM_PROMPT, agent=agent
        )
