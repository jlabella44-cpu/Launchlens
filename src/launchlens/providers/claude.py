# src/launchlens/providers/claude.py
"""
Anthropic Claude provider — used for listing copy generation.

Model: claude-sonnet-4-6 (latest capable model per environment config).
Context is serialized into the user message so Claude has full listing metadata.
"""
import json

import anthropic

from launchlens.config import settings
from launchlens.services.metrics import record_provider_call

from .base import LLMProvider

_MODEL = "claude-sonnet-4-6"
_SYSTEM_PROMPT = (
    "You are an expert real estate copywriter. "
    "Write compelling, accurate, and legally compliant listing descriptions. "
    "Avoid Fair Housing Act violations. Be specific about features, never generic."
)


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str = None):
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )

    async def complete(self, prompt: str, context: dict) -> str:
        context_str = json.dumps(context, indent=2) if context else ""
        user_content = f"{prompt}\n\nContext:\n{context_str}" if context_str else prompt

        try:
            message = await self._client.messages.create(
                model=_MODEL,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            record_provider_call("claude", True)
            return message.content[0].text
        except Exception:
            record_provider_call("claude", False)
            raise
