# src/listingjet/providers/base.py
"""
Provider ABCs for external service integrations.

TemplateProvider — flyer/social asset rendering (Canva, HTML/Chromium)
"""
from abc import ABC, abstractmethod


class ImageEditProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def remove_object(self, image_url: str, object_description: str) -> bytes:
        """Remove an object from an image. Returns edited image bytes (JPEG/PNG)."""
        ...

    @abstractmethod
    async def enhance(self, image_url: str, enhancement: str) -> bytes:
        """Enhance an image (brighten, fix lighting, improve quality). Returns edited bytes."""
        ...


class VirtualStagingProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def stage_image(
        self,
        image_url: str,
        room_type: str,
        style: str = "modern",
    ) -> bytes:
        """Transform an empty/unfurnished room photo into a staged version.

        Args:
            image_url: URL or S3 key of the source image.
            room_type: Room label from vision analysis (living_room, kitchen, etc.)
            style: Staging style (modern, contemporary, minimalist, coastal, etc.)

        Returns:
            Raw PNG/JPEG bytes of the staged image.
        """
        ...


class TemplateProvider(ABC):
    @abstractmethod
    async def render(self, template_id: str, data: dict) -> bytes:
        """Render a template and return raw bytes (PDF or PNG)."""
        ...
