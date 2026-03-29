"""
Fallback provider wrappers.

FallbackVisionProvider and FallbackLLMProvider try a primary provider first,
then transparently fall back to a secondary provider on any exception.
"""

from .base import LLMProvider, VisionLabel, VisionProvider


class FallbackVisionProvider(VisionProvider):
    """Tries *primary*; on failure delegates to *fallback*."""

    def __init__(self, primary: VisionProvider, fallback: VisionProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    async def analyze(self, image_url: str) -> list[VisionLabel]:
        try:
            return await self.primary.analyze(image_url)
        except Exception:
            return await self.fallback.analyze(image_url)

    async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
        try:
            return await self.primary.analyze_with_prompt(image_url, prompt)
        except Exception:
            return await self.fallback.analyze_with_prompt(image_url, prompt)


class FallbackLLMProvider(LLMProvider):
    """Tries *primary*; on failure delegates to *fallback*."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    async def complete(self, prompt: str, context: dict, temperature: float | None = None, system_prompt: str | None = None) -> str:
        try:
            return await self.primary.complete(prompt, context, temperature=temperature, system_prompt=system_prompt)
        except Exception:
            return await self.fallback.complete(prompt, context, temperature=temperature, system_prompt=system_prompt)
