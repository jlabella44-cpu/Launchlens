# src/listingjet/providers/mock.py
"""Mock provider implementations for tests and local development."""
import typing

from pydantic import BaseModel

from .base import ImageEditProvider, LLMProvider, TemplateProvider, VirtualStagingProvider


def _defaults_for(schema: type[BaseModel], seed: int = 0) -> dict:
    """Build a dict of schema-shaped default values for a Pydantic model.

    str -> "mock" (or the first enum literal), int -> 1, float -> 0.5,
    bool -> False, list -> [], nested BaseModel -> recurse.
    """
    import enum

    data: dict = {}
    for name, field in schema.model_fields.items():
        ann = field.annotation
        origin = typing.get_origin(ann)
        if isinstance(ann, type) and issubclass(ann, enum.Enum):
            data[name] = list(ann)[0].value
        elif isinstance(ann, type) and issubclass(ann, BaseModel):
            data[name] = _defaults_for(ann, seed)
        elif origin is list or ann is list:
            data[name] = []
        elif ann is str:
            data[name] = "mock"
        elif ann is bool:
            data[name] = False
        elif ann is int:
            data[name] = 1
        elif ann is float:
            data[name] = 0.5
        elif field.default is not None and field.default.__class__.__name__ != "PydanticUndefinedType":
            data[name] = field.default
        else:
            data[name] = None
    return data

class MockLLMProvider(LLMProvider):
    async def complete(self, prompt: str, context: dict, temperature: float | None = None, system_prompt: str | None = None) -> str:
        return "Stunning home with modern finishes and abundant natural light."


class MockImageEditProvider(ImageEditProvider):
    provider_name = "mock"

    async def remove_object(self, image_url: str, object_description: str) -> bytes:
        return b"\xff\xd8\xff\xe0mock-edited-jpeg"

    async def enhance(self, image_url: str, enhancement: str) -> bytes:
        return b"\xff\xd8\xff\xe0mock-enhanced-jpeg"


class MockVirtualStagingProvider(VirtualStagingProvider):
    provider_name = "mock"

    async def stage_image(self, image_url: str, room_type: str, style: str = "modern") -> bytes:
        return b"\xff\xd8\xff\xe0mock-staged-jpeg-" + f"{room_type}-{style}".encode()


class MockTemplateProvider(TemplateProvider):
    async def render(self, template_id: str, data: dict) -> bytes:
        return b"%PDF-mock-content"


class MockClaudeClient:
    """Mock for ClaudeClient. Tests can queue exact responses per schema via
    `responses: dict[type, list[BaseModel]]` — each call to complete_json/analyze_images
    pops the next queued instance for that schema, falling back to schema-default generation."""

    def __init__(self):
        self.responses: dict[type, list[BaseModel]] = {}
        # analyze_images only: map the first image URL to an exact response.
        # Use this instead of `responses` when calls run concurrently and the
        # queue order is not guaranteed to match the caller's submit order.
        self.by_url: dict[str, BaseModel] = {}
        self._seed = 0

    async def complete_text(self, prompt: str, *, system=None, model=None, max_tokens=4096, agent=None) -> str:
        return "Stunning home with modern finishes and abundant natural light."

    async def _next(self, schema: type[BaseModel]) -> BaseModel:
        queue = self.responses.get(schema)
        if queue:
            return queue.pop(0)
        self._seed += 1
        return schema.model_validate(_defaults_for(schema, self._seed))

    async def complete_json(self, prompt: str, schema: type[BaseModel], *, system=None, model=None, max_tokens=4096, agent=None) -> BaseModel:
        return await self._next(schema)

    async def analyze_images(self, image_urls: list[str], prompt: str, schema: type[BaseModel], *, system=None, model=None, max_tokens=4096, agent=None) -> BaseModel:
        if not image_urls:
            raise ValueError("image_urls must be non-empty")
        if image_urls[0] in self.by_url:
            return self.by_url[image_urls[0]]
        return await self._next(schema)
