# src/launchlens/providers/base.py
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


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, context: dict) -> str:
        """Return a text completion for the given prompt and context."""
        ...


class TemplateProvider(ABC):
    @abstractmethod
    async def render(self, template_id: str, data: dict) -> bytes:
        """Render a template and return raw bytes (PDF or PNG)."""
        ...
