# Session 18: Fix Stubbed Production Code — Social Cuts, Canva Provider, Mocks

## Context
Three production code paths return placeholder/mock data instead of real output:
1. Social cuts agent returns truncated bytes instead of FFmpeg-cropped video
2. Template provider factory always returns MockTemplateProvider even when Canva key is set
3. Mock vision provider returns `"{}"` which breaks floorplan extraction

## Task 1: Implement Real Video Cutting
**File:** `src/launchlens/agents/social_cuts.py`

`VideoCutter.create_cut()` (lines 49-52) returns `source_bytes[:max_duration * 1000]`. Replace with FFmpeg:

```python
import subprocess, tempfile, os

class VideoCutter:
    def create_cut(self, source_bytes: bytes, width: int, height: int, max_duration: int) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as src:
            src.write(source_bytes)
            src_path = src.name
        dst_path = src_path + ".out.mp4"
        try:
            subprocess.run([
                "ffmpeg", "-i", src_path,
                "-t", str(max_duration),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "fast", "-c:a", "aac",
                "-y", dst_path,
            ], check=True, capture_output=True)
            with open(dst_path, "rb") as f:
                return f.read()
        finally:
            for p in (src_path, dst_path):
                if os.path.exists(p): os.unlink(p)
```

Also fix line 86: replace `b"placeholder"` with `self._storage.download(video.s3_key)`.

The Dockerfile already installs FFmpeg — verify with `docker-compose exec api ffmpeg -version`.

## Task 2: Wire Canva Provider into Factory
**File:** `src/launchlens/providers/factory.py` lines 29-34

Currently always returns `MockTemplateProvider`. The `CanvaTemplateProvider` exists at `src/launchlens/providers/canva.py`. Fix the factory:

```python
def get_template_provider() -> TemplateProvider:
    if settings.use_mock_providers:
        from .mock import MockTemplateProvider
        return MockTemplateProvider()
    if settings.canva_api_key:
        from .canva import CanvaTemplateProvider
        return CanvaTemplateProvider(api_key=settings.canva_api_key, llm_provider=get_llm_provider())
    from .mock import MockTemplateProvider
    return MockTemplateProvider()
```

## Task 3: Improve Mock Vision Provider
**File:** `src/launchlens/providers/mock.py`

`analyze_with_prompt()` returns `"{}"`. The floorplan agent parses this as empty rooms. Return realistic mock data:

```python
async def analyze_with_prompt(self, image_url: str, prompt: str) -> str:
    return json.dumps({
        "rooms": [
            {"label": "living_room", "polygon": [[0,0],[0.5,0],[0.5,0.5],[0,0.5]], "width_meters": 5, "height_meters": 4},
            {"label": "kitchen", "polygon": [[0.5,0],[1,0],[1,0.5],[0.5,0.5]], "width_meters": 4, "height_meters": 4},
        ],
        "overall_width_meters": 10, "overall_height_meters": 8,
    })
```

## Verification
- Run social cuts agent with a test video → produces actual cropped MP4 files for each platform
- Set `CANVA_API_KEY=test` → factory returns `CanvaTemplateProvider`
- Unset `CANVA_API_KEY` → factory falls back to `MockTemplateProvider`
- Floorplan agent with mock provider → generates valid scene with 2+ rooms (not empty)
