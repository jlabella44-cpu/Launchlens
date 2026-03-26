# src/launchlens/providers/mock.py
"""Mock provider implementations for tests and local development."""
from .base import VisionLabel, VisionProvider, LLMProvider, TemplateProvider


class MockVisionProvider(VisionProvider):
    async def analyze(self, image_url: str) -> list[VisionLabel]:
        return [
            VisionLabel(name="living room", confidence=0.97, category="room"),
            VisionLabel(name="hardwood floor", confidence=0.91, category="feature"),
            VisionLabel(name="natural light", confidence=0.88, category="quality"),
        ]


class MockLLMProvider(LLMProvider):
    async def complete(self, prompt: str, context: dict) -> str:
        return "Stunning home with modern finishes and abundant natural light."


class MockTemplateProvider(TemplateProvider):
    async def render(self, template_id: str, data: dict) -> bytes:
        return b"%PDF-mock-content"
