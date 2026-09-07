# src/listingjet/providers/mock.py
"""Mock provider implementations for tests and local development."""
import tempfile
import typing
from pathlib import Path

from pydantic import BaseModel

from .base import ImageEditProvider, TemplateProvider, VirtualStagingProvider


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


class MockRunwayClient:
    """Mock for RunwayClient. Tasks resolve SUCCEEDED unless their model is
    listed in `fail_models`, in which case they resolve FAILED.

    `download` returns real mp4 bytes — a 2s 320x180 solid-colour clip built
    with ffmpeg via `video_stitcher.build_still_clip` — so pipeline code that
    stitches/probes the downloaded clip works end-to-end against the mock.
    The clip is generated once and cached on the instance.
    """

    provider_name = "runway"

    def __init__(self):
        self.submitted: list[dict] = []
        self.fail_models: set[str] = set()
        self._task_models: dict[str, str] = {}
        self._n = 0
        self._clip_bytes: bytes | None = None

    async def image_to_video(
        self,
        image_url: str,
        prompt: str,
        *,
        model: str,
        duration: int,
        ratio: str = "1280:720",
        audio: bool | None = None,
    ) -> str:
        self._n += 1
        task_id = f"mock-task-{self._n}"
        self.submitted.append({
            "image_url": image_url,
            "prompt": prompt,
            "model": model,
            "duration": duration,
            "ratio": ratio,
            "audio": audio,
        })
        self._task_models[task_id] = model
        return task_id

    async def get_task(self, task_id: str) -> dict:
        model = self._task_models.get(task_id)
        if model in self.fail_models:
            return {"status": "FAILED", "failure": "mock failure", "failureCode": "MOCK"}
        return {"status": "SUCCEEDED", "output": [f"mock://clip/{task_id}"]}

    async def wait(self, task_id: str, *, timeout_s: float = 900.0, poll_s: float = 5.0) -> list[str]:
        from .runway import RunwayTaskFailed

        task = await self.get_task(task_id)
        if task["status"] == "FAILED":
            raise RunwayTaskFailed(
                task["failure"], task_id=task_id, failure_code=task.get("failureCode"),
            )
        return task["output"]

    async def download(self, url: str) -> bytes:
        if self._clip_bytes is None:
            from PIL import Image

            from listingjet.services.video_stitcher import build_still_clip

            with tempfile.TemporaryDirectory() as tmpdir:
                png_path = str(Path(tmpdir) / "mock.png")
                mp4_path = str(Path(tmpdir) / "mock.mp4")
                Image.new("RGB", (320, 180), color=(30, 144, 255)).save(png_path)
                build_still_clip(png_path, mp4_path, duration_s=2.0, width=320, height=180)
                self._clip_bytes = Path(mp4_path).read_bytes()
        return self._clip_bytes

    async def aclose(self) -> None:
        pass
