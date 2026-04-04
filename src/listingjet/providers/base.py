# src/listingjet/providers/base.py
"""
Provider ABCs for external service integrations.

VisionProvider  — photo analysis (Google Vision, GPT-4V)
LLMProvider     — text generation (Claude, GPT-4)
TemplateProvider — flyer/social asset rendering (Canva, HTML/Chromium)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VisionLabel:
    name: str
    confidence: float
    category: str  # e.g. "room", "feature", "quality"


class VisionProvider(ABC):
    @abstractmethod
    async def analyze(self, image_url: str) -> list[VisionLabel]:
        """Return labels for the given image URL."""
        ...

    async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
        """Send an image with a custom prompt. Returns raw text response."""
        raise NotImplementedError


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        context: dict,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Return a text completion for the given prompt and context.

        Args:
            temperature: 0.0-1.0, controls creativity. None = provider default.
            system_prompt: Override the default system prompt. None = provider default.
        """
        ...


class VirtualStagingProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def stage_image(
        self,
        image_url: str,
        room_type: str,
        style: str = "modern",
    ) -> str:
        """Transform an empty/unfurnished room photo into a staged version.

        Args:
            image_url: URL or S3 key of the source image.
            room_type: Room label from vision analysis (living_room, kitchen, etc.)
            style: Staging style (modern, contemporary, minimalist, coastal, etc.)

        Returns:
            URL of the staged image.
        """
        ...


class TemplateProvider(ABC):
    @abstractmethod
    async def render(self, template_id: str, data: dict) -> bytes:
        """Render a template and return raw bytes (PDF or PNG)."""
        ...
