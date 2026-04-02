# src/listingjet/providers/mock.py
"""Mock provider implementations for tests and local development."""
import uuid
from pathlib import Path

from .base import LLMProvider, TemplateProvider, VideoClipProvider, VisionLabel, VisionProvider


class MockVisionProvider(VisionProvider):
    async def analyze(self, image_url: str) -> list[VisionLabel]:
        return [
            VisionLabel(name="living room", confidence=0.97, category="room"),
            VisionLabel(name="hardwood floor", confidence=0.91, category="feature"),
            VisionLabel(name="natural light", confidence=0.88, category="quality"),
        ]

    async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
        return (
            '{"rooms": ['
            '{"name": "Living Room", "area_sqft": 280, "features": ["hardwood floors", "crown molding", "bay window"]},'
            '{"name": "Kitchen", "area_sqft": 180, "features": ["granite countertops", "stainless appliances", "island"]},'
            '{"name": "Primary Bedroom", "area_sqft": 220, "features": ["walk-in closet", "en-suite bath", "vaulted ceiling"]},'
            '{"name": "Bedroom 2", "area_sqft": 160, "features": ["carpet", "closet"]},'
            '{"name": "Primary Bath", "area_sqft": 95, "features": ["double vanity", "soaking tub", "walk-in shower"]},'
            '{"name": "Half Bath", "area_sqft": 35, "features": ["pedestal sink"]},'
            '{"name": "Garage", "area_sqft": 400, "features": ["2-car", "epoxy floor"]}'
            '], "total_sqft": 1370, "bedrooms": 2, "bathrooms": 1.5}'
        )


class MockLLMProvider(LLMProvider):
    async def complete(self, prompt: str, context: dict, temperature: float | None = None, system_prompt: str | None = None) -> str:
        return "Stunning home with modern finishes and abundant natural light."


class MockTemplateProvider(TemplateProvider):
    async def render(self, template_id: str, data: dict) -> bytes:
        return b"%PDF-mock-content"


class MockKlingProvider(VideoClipProvider):
    """Returns a local test video fixture instead of calling Kling API."""

    FIXTURE_PATH = str(
        Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures" / "test_clip.mp4"
    )

    async def generate_clip(
        self,
        image_url: str,
        prompt: str,
        negative_prompt: str = "",
        camera_control: dict | None = None,
        duration: int = 5,
        mode: str = "pro",
    ) -> str:
        return f"mock_task_{uuid.uuid4().hex[:8]}"

    async def poll_task(
        self,
        task_id: str,
        timeout: int = 300,
        interval: int = 5,
    ) -> str | None:
        return self.FIXTURE_PATH
