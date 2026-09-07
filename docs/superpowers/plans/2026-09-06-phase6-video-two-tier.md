# Phase 6: Two-Tier Video (ffmpeg baseline + Runway add-on) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every listing gets a free ffmpeg Ken Burns tour video; listings with the `ai_video_tour` add-on get up to six Runway-generated shots stitched into the same tour, with Ken Burns fallback per failed shot and resumable task ids. Kling and the old 12-clip Kling agent go away.

**Architecture:** `services/video_stitcher.py` grows a Ken Burns clip builder and a duration-aware xfade stitcher (all ffmpeg subprocess, run under `asyncio.to_thread`). `agents/video_baseline.py` builds the tour from packaged photos. `providers/runway.py` is a thin httpx client for `/v1/image_to_video` + `/v1/tasks/{id}`; `agents/video_ai.py` submits shots, persists task ids on `VideoAsset.metadata_` immediately, polls, downloads, falls back, and re-stitches over the baseline. `social_cuts` runs after whichever tier finished. `VideoAsset.video_type` becomes `"tour"`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, ffmpeg (subprocess), httpx + pytest-httpx, Runway Dev API (`X-Runway-Version: 2024-11-06`).

**Spec:** `docs/superpowers/specs/2026-09-05-free-tier-rework-design.md` — "Phase 6: video".

## Global Constraints

- Branch `feat/video-two-tier` off `feat/content-social` (PR #310). PR targets `feat/content-social`. Never push to `main`; never merge; never amend published commits.
- **Runway model routing (ruling — the spec's "Kling 3.0" is not available on Runway's API):** exteriors and drone shots → `veo3.1_fast` (`duration=6`, `audio=false`, `ratio="1280:720"`, 10 credits/s); interiors → `gen4_turbo` (`duration=5`, `ratio="1280:720"`, 5 credits/s). Both ids come from settings (`runway_exterior_model`, `runway_interior_model`) so the router is a config change. Credits cost $0.01 each; rates live in `config/ai_rates.py` as USD per generated second: `{"gen4_turbo": 0.05, "veo3.1_fast": 0.10}`.
- Runway request shape: `POST {base}/v1/image_to_video` JSON `{"model", "promptImage": <url>, "promptText": <≤1000 chars>, "duration", "ratio", "audio"?}` with headers `Authorization: Bearer <key>`, `X-Runway-Version: 2024-11-06`, `Content-Type: application/json` → `{"id": "..."}`. `GET {base}/v1/tasks/{id}` → `{"status": PENDING|THROTTLED|RUNNING|SUCCEEDED|FAILED|CANCELLED, "output": [url,...], "failure": str?, "failureCode": str?, "progress": float?}`. Base `https://api.dev.runwayml.com`. Output URLs expire in 24–48 h: download immediately.
- Every ffmpeg invocation goes through `settings.ffmpeg_bin` (default `"ffmpeg"`); ffprobe is `settings.ffmpeg_bin` with `ffmpeg` → `ffprobe` swapped in the basename. Local dev machine: `FFMPEG_BIN=C:/Users/label/tools/ffmpeg/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe` in `.env` (gitignored). CI installs ffmpeg with apt.
- Tests that shell out to ffmpeg are marked `@pytest.mark.ffmpeg` and use the `ffmpeg_available` fixture (skip with a clear message when the binary is missing; CI has it).
- CPU/ffmpeg work never runs on the event loop: `await asyncio.to_thread(...)`. No DB transaction is held across ffmpeg or Runway calls (load → work → save).
- Baseline output: 1920x1080, 30 fps, H.264 `yuv420p`, 3.0 s per photo, 0.5 s xfade, end card appended (5 s), silent unless `settings.video_music_enabled` and `settings.video_music_path` point to a file (mixed at -18 dB). No music file ships in this phase.
- Tour key is always `videos/{listing_id}/tour.mp4`; exactly one `VideoAsset` row per listing with `video_type="tour"` (upsert; legacy `"ai_generated"` rows are migrated by 056).
- `VideoAsset.chapters` keeps the frontend shape `[{"time": <int seconds>, "label": <room>}]` (see `video-player.tsx`). The clip manifest lives in `VideoAsset.metadata_["clips"]`: `[{"asset_id", "room", "start_s", "end_s", "source": "ken_burns"|"runway", "model"?: str}]`; Runway task ids in `metadata_["runway_tasks"]: {asset_id: task_id}`; `metadata_["tier"]: "baseline"|"ai"`.
- Every Bash call passes an explicit timeout; never two pytest processes at once; full suite 0 failed; `ruff check src tests alembic` clean.
- Commit trailer on every commit:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FN81v1ehP7Snv3UsWaRf9D
  ```

---

## File map

| File | Responsibility |
|---|---|
| `src/listingjet/config/__init__.py` | `ffmpeg_bin`, `runway_api_key`, `runway_interior_model`, `runway_exterior_model`, `video_music_enabled`, `video_music_path`; drop `kling_*`, `video_score_floor` |
| `src/listingjet/config/ai_rates.py`, `services/metrics.py` | `VIDEO_SECOND_RATES`, `record_video_seconds(model_id, seconds, agent)`; drop `LEGACY_CALL_RATES["kling"]` |
| `alembic/versions/056_video_asset_metadata.py` | `video_assets.metadata JSONB` (attr `metadata_`), `UPDATE video_assets SET video_type='tour' WHERE video_type='ai_generated'` |
| `src/listingjet/services/video_stitcher.py` | `ffmpeg_cmd()`, `probe_duration()`, `build_ken_burns_clip()`, `build_still_clip()`, `VideoStitcher.stitch_xfade()` (duration-aware), keep `_stitch_hard_cuts` |
| `src/listingjet/providers/runway.py` (new), `providers/mock.py` (`MockRunwayClient`), `providers/factory.py` (`get_runway()`) | Runway client |
| `src/listingjet/agents/video_baseline.py` (new) | free tour |
| `src/listingjet/agents/video_ai.py` (new) | add-on tour |
| `src/listingjet/agents/video_template.py` | keep prompts/order/buckets/`get_prompt_for_room`; drop `NEGATIVE_PROMPT`, `ROOM_CAMERA_CONTROLS`, `get_camera_control`, `VideoTemplate`, `STANDARD_60S` |
| `src/listingjet/agents/social_cuts.py` | `to_thread`, `ffmpeg_bin`, requires updated |
| Delete: `agents/video.py`, `providers/kling.py`, `tests/test_agents/test_video.py`, `tests/test_providers/test_kling.py` | |
| `src/listingjet/pipeline/definition.py`, `steps.py`, `runner.py` (`_gated_off`) | `video_baseline` + `video_ai` replace `video`; gate `video` branch removed |
| `.github/workflows/test.yml` | apt-get ffmpeg step |
| `frontend/src` | `"ai_generated"` → `"tour"` where displayed |
| tests | `tests/test_services/test_video_stitcher.py`, `tests/test_providers/test_runway.py`, `tests/test_agents/test_video_baseline.py`, `tests/test_agents/test_video_ai.py`, `tests/conftest.py` (`ffmpeg_available`), updates to definition/runner_scale/social_cuts/metrics/config tests |

---

### Task 1: Settings, rates, migration 056, stitcher primitives

**Files:**
- Modify: `src/listingjet/config/__init__.py`, `src/listingjet/config/ai_rates.py`, `src/listingjet/services/metrics.py`, `src/listingjet/services/video_stitcher.py`, `src/listingjet/models/video_asset.py`, `.env.example`, `render.yaml` (env list), `tests/conftest.py`
- Create: `alembic/versions/056_video_asset_metadata.py`, `tests/test_services/test_video_stitcher.py`
- Modify tests: `tests/test_config/*` (kling fields gone), `tests/test_services/test_metrics.py` (rates)

**Interfaces:**
- Consumes: `IMAGE_CALL_RATES`/`record_image_call` pattern in `services/metrics.py` (Phase 4).
- Produces:
  - `settings.ffmpeg_bin: str = "ffmpeg"`, `settings.runway_api_key: str = ""`, `settings.runway_interior_model: str = "gen4_turbo"`, `settings.runway_exterior_model: str = "veo3.1_fast"`, `settings.video_music_enabled: bool = False`, `settings.video_music_path: str = ""`. `validate_provider_keys` unchanged (Runway key checked lazily by `get_runway()`).
  - `ai_rates.VIDEO_SECOND_RATES = {"gen4_turbo": 0.05, "veo3.1_fast": 0.10}`; `metrics.record_video_seconds(model_id: str, seconds: float, agent: str) -> float` (returns USD, warns once on unknown id, records cost 0).
  - `VideoAsset.metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)`.
  - `video_stitcher.ffmpeg_cmd() -> str`, `ffprobe_cmd() -> str`, `probe_duration(path) -> float`, `build_ken_burns_clip(image_path, out_path, *, duration_s=3.0, index=0, width=1920, height=1080, fps=30) -> str` (direction cycles by `index % 4`: zoom-in centre, pan left→right, zoom-out, pan top→bottom), `build_still_clip(image_path, out_path, *, duration_s=5.0, width=1920, height=1080, fps=30) -> str`, `VideoStitcher.stitch_xfade(clips: list[tuple[str, float]], *, transition="fade", transition_s=0.5, music_path=None, music_db=-18.0, width=1920, height=1080, fps=30) -> bytes`.
  - `tests/conftest.py::ffmpeg_available` fixture + `ffmpeg` marker registered in `pyproject.toml` (`[tool.pytest.ini_options] markers`).

- [ ] **Step 1: Failing tests** — `tests/test_services/test_video_stitcher.py`

```python
import os
import shutil

import pytest
from PIL import Image

from listingjet.config import settings
from listingjet.services import video_stitcher as vs


@pytest.fixture
def png(tmp_path):
    def make(name: str, color=(200, 80, 40), size=(640, 360)) -> str:
        p = tmp_path / name
        Image.new("RGB", size, color).save(p)
        return str(p)
    return make


pytestmark = pytest.mark.ffmpeg


def test_ffmpeg_cmd_uses_setting(monkeypatch):
    monkeypatch.setattr(settings, "ffmpeg_bin", "C:/x/ffmpeg.exe")
    assert vs.ffmpeg_cmd() == "C:/x/ffmpeg.exe"
    assert vs.ffprobe_cmd() == "C:/x/ffprobe.exe"


def test_ken_burns_clip_has_requested_duration(ffmpeg_available, png, tmp_path):
    out = vs.build_ken_burns_clip(png("a.png"), str(tmp_path / "a.mp4"), duration_s=2.0, index=1, width=320, height=180, fps=30)
    assert os.path.getsize(out) > 0
    assert abs(vs.probe_duration(out) - 2.0) < 0.15


def test_still_clip(ffmpeg_available, png, tmp_path):
    out = vs.build_still_clip(png("e.png"), str(tmp_path / "e.mp4"), duration_s=1.0, width=320, height=180)
    assert abs(vs.probe_duration(out) - 1.0) < 0.15


def test_stitch_xfade_total_duration(ffmpeg_available, png, tmp_path):
    clips = []
    for i in range(3):
        p = vs.build_ken_burns_clip(png(f"{i}.png", color=(i * 60, 100, 150)), str(tmp_path / f"{i}.mp4"), duration_s=2.0, index=i, width=320, height=180)
        clips.append((p, 2.0))
    data = vs.VideoStitcher().stitch_xfade(clips, transition_s=0.5, width=320, height=180)
    out = tmp_path / "tour.mp4"
    out.write_bytes(data)
    # 3 × 2.0 s minus 2 overlaps of 0.5 s
    assert abs(vs.probe_duration(str(out)) - 5.0) < 0.2


def test_stitch_xfade_single_clip_passthrough(ffmpeg_available, png, tmp_path):
    p = vs.build_still_clip(png("s.png"), str(tmp_path / "s.mp4"), duration_s=1.0, width=320, height=180)
    data = vs.VideoStitcher().stitch_xfade([(p, 1.0)])
    assert data == open(p, "rb").read()
```

`tests/conftest.py`:

```python
import shutil

@pytest.fixture
def ffmpeg_available():
    from listingjet.config import settings
    if shutil.which(settings.ffmpeg_bin) is None:
        pytest.skip(f"ffmpeg not found at {settings.ffmpeg_bin!r}; set FFMPEG_BIN")
    return settings.ffmpeg_bin
```

`pyproject.toml` `[tool.pytest.ini_options]` gets `markers = ["ffmpeg: shells out to ffmpeg"]` (append to any existing list). Also a metrics test: `record_video_seconds("gen4_turbo", 5.0, "video_ai") == 0.25` and unknown id → 0.0 with one warning; a config test that `Settings(ffmpeg_bin="x").ffmpeg_bin == "x"` and `kling_access_key` no longer exists.

- [ ] **Step 2: RED** — `.venv/Scripts/python.exe -m pytest tests/test_services/test_video_stitcher.py -q -p no:cacheprovider` (AttributeError on `ffmpeg_cmd`).

- [ ] **Step 3: Implement** `video_stitcher.py` (keep the class and `_stitch_hard_cuts`; replace hard-coded `"ffmpeg"`):

```python
import json
import os
import subprocess
import tempfile

from listingjet.config import settings


def ffmpeg_cmd() -> str:
    return settings.ffmpeg_bin


def ffprobe_cmd() -> str:
    head, tail = os.path.split(settings.ffmpeg_bin)
    return os.path.join(head, tail.replace("ffmpeg", "ffprobe", 1)) if head else tail.replace("ffmpeg", "ffprobe", 1)


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {proc.stderr.decode(errors='replace')[-2000:]}")


def probe_duration(path: str) -> float:
    proc = subprocess.run(
        [ffprobe_cmd(), "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, check=True,
    )
    return float(json.loads(proc.stdout)["format"]["duration"])


_KB_EXPR = [
    # zoom in on centre
    ("min(zoom+0.0015,1.25)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # pan left -> right at fixed zoom
    ("1.15", "(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"),
    # zoom out from 1.25
    ("if(eq(on,1),1.25,max(zoom-0.0015,1.0))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # pan top -> bottom at fixed zoom
    ("1.15", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*on/{frames}"),
]


def build_ken_burns_clip(image_path: str, out_path: str, *, duration_s: float = 3.0, index: int = 0,
                         width: int = 1920, height: int = 1080, fps: int = 30) -> str:
    frames = int(round(duration_s * fps))
    z, x, y = (e.format(frames=frames) for e in _KB_EXPR[index % len(_KB_EXPR)])
    vf = (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},"
        f"format=yuv420p"
    )
    _run([ffmpeg_cmd(), "-y", "-loop", "1", "-i", image_path, "-vf", vf, "-frames:v", str(frames),
          "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-r", str(fps), "-an", out_path])
    return out_path


def build_still_clip(image_path: str, out_path: str, *, duration_s: float = 5.0,
                     width: int = 1920, height: int = 1080, fps: int = 30) -> str:
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p")
    _run([ffmpeg_cmd(), "-y", "-loop", "1", "-i", image_path, "-t", f"{duration_s:.3f}", "-vf", vf,
          "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-r", str(fps), "-an", out_path])
    return out_path


class VideoStitcher:
    def __init__(self, transition_duration: float = 0.5, music_volume: float = 0.2):
        self._transition_duration = transition_duration
        self._music_volume = music_volume

    def stitch_xfade(self, clips: list[tuple[str, float]], *, transition: str = "fade", transition_s: float = 0.5,
                     music_path: str | None = None, music_db: float = -18.0,
                     width: int = 1920, height: int = 1080, fps: int = 30) -> bytes:
        if not clips:
            raise ValueError("No clips to stitch")
        if len(clips) == 1:
            with open(clips[0][0], "rb") as f:
                return f.read()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.mp4")
            inputs: list[str] = []
            parts: list[str] = []
            for i, (path, _) in enumerate(clips):
                inputs += ["-i", path]
                parts.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                             f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{i}];")
            prev, elapsed = "v0", clips[0][1]
            for i in range(1, len(clips)):
                offset = elapsed - transition_s
                parts.append(f"[{prev}][v{i}]xfade=transition={transition}:duration={transition_s}:offset={offset:.3f}[x{i}];")
                prev = f"x{i}"
                elapsed = offset + clips[i][1]
            graph = "".join(parts).rstrip(";")
            cmd = [ffmpeg_cmd(), "-y", *inputs]
            maps = ["-map", f"[{prev}]"]
            if music_path and os.path.exists(music_path):
                cmd += ["-stream_loop", "-1", "-i", music_path]
                graph += f";[{len(clips)}:a]volume={music_db}dB[a]"
                maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "128k", "-shortest"]
            cmd += ["-filter_complex", graph, *maps, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-r", str(fps), out]
            _run(cmd)
            with open(out, "rb") as f:
                return f.read()

    # keep the existing stitch()/_stitch_hard_cuts() with "ffmpeg" replaced by ffmpeg_cmd()
```

`social_cuts.VideoCutter` and any other `"ffmpeg"` literal switch to `ffmpeg_cmd()` in Task 5 (not here).

Migration `056_video_asset_metadata.py` (`down_revision="055_vision_result_analysis"`): `op.add_column("video_assets", sa.Column("metadata", postgresql.JSONB, nullable=True))`; `op.execute("UPDATE video_assets SET video_type='tour' WHERE video_type='ai_generated'")`; downgrade drops the column (leave the value rename in place, documented).

- [ ] **Step 4: GREEN** — stitcher, metrics, config tests; `.venv/Scripts/alembic.exe upgrade head` on the dev DB and `alembic heads` = `056_video_asset_metadata`; ruff.
- [ ] **Step 5: Commit** — `feat(video): ffmpeg Ken Burns primitives, video rates, VideoAsset.metadata (056)`.

---

### Task 2: Runway client + mock + factory

**Files:**
- Create: `src/listingjet/providers/runway.py`, `tests/test_providers/test_runway.py`
- Modify: `src/listingjet/providers/mock.py` (`MockRunwayClient`), `providers/factory.py` (`get_runway()`), `providers/__init__.py`

**Interfaces:**
- Produces:
  - `class RunwayError(Exception)`; `class RunwayTaskFailed(RunwayError)` with `.task_id`, `.failure_code`.
  - `RunwayClient(api_key: str | None = None, *, base_url="https://api.dev.runwayml.com", version="2024-11-06", timeout_s=60.0)`; `async image_to_video(image_url: str, prompt: str, *, model: str, duration: int, ratio: str = "1280:720", audio: bool | None = None) -> str` (task id; 4xx → `RunwayError` with body text, no retry; 429/5xx → up to 3 retries with 2/4/8 s backoff); `async get_task(task_id) -> dict`; `async wait(task_id, *, timeout_s=900.0, poll_s=5.0) -> list[str]` (poll with `poll_s` growing ×1.5 to max 20 s; SUCCEEDED → `output` urls; FAILED/CANCELLED → `RunwayTaskFailed`; timeout → `RunwayError`); `async download(url) -> bytes` (httpx GET, 120 s timeout); `async aclose()`.
  - `MockRunwayClient()` with `.submitted: list[dict]`, `.fail_models: set[str]` (tasks for those models resolve FAILED), `image_to_video` returns `f"mock-task-{n}"`, `wait` returns `[f"mock://clip/{task_id}"]`, `download("mock://...")` returns bytes of a 2 s 320x180 solid-colour clip built with ffmpeg (`build_still_clip` on a generated PNG, cached in the instance) — this keeps the mock e2e stitchable.
  - `factory.get_runway() -> RunwayClient | MockRunwayClient` (mock when `use_mock_providers`; raise `RuntimeError("RUNWAY_API_KEY is not set")` when real and key empty).

- [ ] **Step 1: Failing tests** (`pytest-httpx` `httpx_mock` fixture; look at `tests/test_providers/test_openai_images.py` for the house style):
  1. `image_to_video` posts to `https://api.dev.runwayml.com/v1/image_to_video` with `Authorization: Bearer k`, `X-Runway-Version: 2024-11-06`, JSON body containing `model`, `promptImage`, `promptText`, `duration`, `ratio` (and `audio` only when passed) → returns `"t1"` from `{"id":"t1"}`.
  2. 400 → `RunwayError` containing the body; exactly one request made.
  3. `wait` polls `GET /v1/tasks/t1`: responses PENDING → RUNNING → SUCCEEDED with `output=["https://cdn/x.mp4"]` → returns the list (patch `asyncio.sleep` to no-op).
  4. `wait` on FAILED with `failureCode: "SAFETY"` → `RunwayTaskFailed` with `.failure_code == "SAFETY"`.
  5. `wait` timeout → `RunwayError` (use `timeout_s=0` with a PENDING response).
  6. `MockRunwayClient.download` returns non-empty bytes whose `probe_duration` ≈ 2 s (mark `ffmpeg`, use `ffmpeg_available`).
- [ ] **Step 2: RED → implement → GREEN → ruff.**
- [ ] **Step 3: Commit** — `feat(providers): Runway image-to-video client with resumable task polling`.

---

### Task 3: `VideoBaselineAgent`

**Files:**
- Create: `src/listingjet/agents/video_baseline.py`, `tests/test_agents/test_video_baseline.py`
- Modify: `src/listingjet/services/endcard.py` (add `endcard_clip(png_bytes, out_path, *, duration_s=ENDCARD_DURATION, width, height) -> str` using `build_still_clip`)

**Interfaces:**
- Consumes: Task 1 stitcher primitives; `PackageSelection.position`; `VisionResult.is_photo/room_label`; `video_template.VIDEO_EXCLUDED_LABELS`; `StorageService.download/upload_bytes`; `BrandKit`; `generate_endcard`.
- Produces: `VideoBaselineAgent(storage=None, stitcher=None, session_factory=None, max_photos=10, clip_s=3.0)`, `agent_name="video_baseline"`, `requires_ai_consent=False`; `execute` returns `{"status": "ready", "video_asset_id", "s3_key", "clip_count", "duration_s"}` or `{"skipped": True, "reason": "no_packaged_photos"}`; event `video_baseline.completed` `{video_asset_id, s3_key, clip_count, duration_s}`; helper `upsert_tour_asset(session, listing, *, s3_key, duration_s, clip_count, chapters, metadata) -> VideoAsset` (shared with Task 4: finds the row with `video_type in ("tour","ai_generated")`, updates or inserts, sets `status="ready"`, `video_type="tour"`); helper `select_baseline_photos(rows) -> list[(asset, vr)]` (position order, skip `vr.is_photo is False`, skip `room_label in VIDEO_EXCLUDED_LABELS`, skip filenames containing floorplan/blueprint/site_plan/diagram, cap `max_photos`); `build_tour(photo_paths_rooms: list[tuple[str, str]], endcard_png: bytes | None, *, clip_s, width, height) -> tuple[bytes, list[dict], list[dict]]` (returns video bytes, `chapters`, `clips` manifest) — pure function run under `to_thread`.

- [ ] **Step 1: Failing tests** (mark `ffmpeg`; real stitcher; `MagicMock` storage whose `download` returns PNG bytes generated with Pillow per key and whose `upload_bytes` records the key):
  1. `test_builds_tour_from_packaged_photos`: 4 packaged assets (one `is_photo=False` document at position 2) → uploaded key `videos/{id}/tour.mp4`, `clip_count == 3`, `duration_s ≈ 3×3.0 − 2×0.5 + 5` (end card), one `VideoAsset` row with `video_type="tour"`, `status="ready"`, `chapters == [{"time":0,"label":<room>}, {"time":2,...}, {"time":5,...}]` (times are `int(round(start_s))`), `metadata_["tier"]=="baseline"`, `metadata_["clips"]` has 3 entries with `source=="ken_burns"`.
  2. `test_skips_without_package`: no `PackageSelection` → skipped result, no upload, no row.
  3. `test_rerun_updates_same_row`: run twice → still one row, `s3_key` unchanged.
  4. `test_caps_at_max_photos`: 12 packaged → `clip_count == 10`.
  5. `test_endcard_appended_when_brand_kit` vs without brand kit (duration differs by 5 s; without brand kit still appends a neutral end card using defaults — decide: **append the end card always**, `generate_endcard()` with defaults when no brand kit).
- [ ] **Step 2: RED → implement.** Flow: session 1 loads listing, ordered `(PackageSelection, Asset, VisionResult)` rows, brand kit → close. Download each asset (`asset.proxy_path or asset.file_path`) via `to_thread(storage.download)` into a `TemporaryDirectory`; `to_thread(build_tour, ...)`; `to_thread(storage.upload_bytes, ...)`; session 2 upserts the asset row and emits. Chapters: `time=int(round(start_s))`, `label=room or "photo"`. Start times: clip `i` starts at `i*(clip_s - 0.5)`.
- [ ] **Step 3: GREEN, ruff, commit** — `feat(agents): VideoBaselineAgent — free Ken Burns tour for every listing`.

---

### Task 4: `VideoAIAgent`, template cleanup, Kling removal

**Files:**
- Create: `src/listingjet/agents/video_ai.py`, `tests/test_agents/test_video_ai.py`
- Modify: `src/listingjet/agents/video_template.py` (drop `NEGATIVE_PROMPT`, `ROOM_CAMERA_CONTROLS`, `get_camera_control`, `VideoTemplate`, `STANDARD_60S`; keep the rest; update its docstring), `src/listingjet/config/ai_rates.py` (drop `LEGACY_CALL_RATES` if only kling remained; adjust `services/metrics.py` fallback accordingly)
- Delete: `src/listingjet/agents/video.py`, `src/listingjet/providers/kling.py`, `tests/test_agents/test_video.py`, `tests/test_providers/test_kling.py`, any `tests/test_agents/test_video_template.py` cases that reference removed names

**Interfaces:**
- Consumes: Task 2 `RunwayClient`/`MockRunwayClient`/`get_runway`; Task 3 `upsert_tour_asset`, `build_ken_burns_clip`, `endcard_clip`, `VideoStitcher.stitch_xfade`; `video_template.get_prompt_for_room`, `WALKTHROUGH_ORDER`, `DRONE_ROOMS`, `EXTERIOR_ROOMS`, `VIDEO_EXCLUDED_LABELS`; `record_video_seconds`.
- Produces: `VideoAIAgent(runway=None, storage=None, stitcher=None, session_factory=None, concurrency=3, max_shots=6)`, `agent_name="video_ai"`, `requires_ai_consent=True`; `select_shots(rows) -> list[Shot]` where `Shot(asset, room, kind: "exterior"|"drone"|"interior")` — 1 best exterior (highest `hero_score`), 1 drone if any, then interiors in `WALKTHROUGH_ORDER` up to `max_shots` total, backfilled with further exteriors; `model_for(kind) -> (model, duration, audio)`: exterior/drone → `(settings.runway_exterior_model, 6, False)`, interior → `(settings.runway_interior_model, 5, None)`; `execute` returns `{"status": "ready", "video_asset_id", "s3_key", "runway_clips": n, "fallback_clips": m, "cost_usd": x}` or `{"skipped": True, "reason": "no_shots"}`; event `video_ai.completed` with the same numbers.

Resume semantics: before submitting, read the existing tour `VideoAsset.metadata_["runway_tasks"]`; for each shot whose `asset_id` already has a task id, skip submission and poll that id. After submitting any new task, immediately write `metadata_["runway_tasks"]` in its own short session (so a crash mid-run leaves ids behind). Per shot: `async with semaphore: task_id = ...; urls = await runway.wait(task_id, timeout_s=600)` → `download(urls[0])` to temp `.mp4`; on `RunwayTaskFailed`/`RunwayError`/timeout → log, build a Ken Burns clip of the same photo (`duration_s = 5.0`), mark `source="ken_burns"`. Cost: `record_video_seconds(model, duration, "video_ai")` per succeeded Runway clip; sum in result. Stitch in walkthrough order with `stitch_xfade` + end card; upload to `videos/{listing_id}/tour.mp4`; `upsert_tour_asset(..., metadata={"tier": "ai", "clips": [...], "runway_tasks": {...}})`; chapters recomputed from actual clip durations.

- [ ] **Step 1: Failing tests** (mark `ffmpeg` where stitching happens; use `MockRunwayClient` and a storage mock as in Task 3):
  1. `test_select_shots_order_and_cap`: 2 exteriors, 1 drone, 6 interiors → 6 shots: best exterior, drone, then 4 interiors in `WALKTHROUGH_ORDER`.
  2. `test_model_routing`: exterior → `(settings.runway_exterior_model, 6, False)`; interior → `(settings.runway_interior_model, 5, None)`.
  3. `test_generates_and_stitches`: 3 shots → 3 `image_to_video` calls with the right models, tour uploaded, row `metadata_["tier"]=="ai"`, three `runway_tasks`, `runway_clips==3`, `cost_usd == 2*0.25 + 0.60` (for 2 interiors + 1 exterior — compute from rates).
  4. `test_failed_shot_falls_back_to_ken_burns`: `fail_models={settings.runway_exterior_model}` → the exterior clip has `source=="ken_burns"`, tour still complete, `fallback_clips==1`.
  5. `test_resume_polls_existing_tasks`: seed a tour row with `metadata_["runway_tasks"]={asset_a: "mock-task-99"}`; run → `image_to_video` NOT called for asset_a (assert on `mock.submitted`), called for the others.
  6. `test_task_ids_persisted_before_polling`: patch `runway.wait` to raise `RuntimeError` after submissions; assert the row's `metadata_["runway_tasks"]` already contains the new ids and the step raised.
- [ ] **Step 2: RED → implement → GREEN.** Then delete the Kling/legacy files, trim `video_template.py`, fix `ai_rates`/`metrics`, and run `grep -rn "kling\|Kling\|KLING\|NEGATIVE_PROMPT\|get_camera_control\|STANDARD_60S\|VideoTemplate\|agents\.video\b\|VideoAgent\b" src tests --include=*.py` → must be empty (except `.env.example`/`render.yaml` lines you also remove).
- [ ] **Step 3: ruff, commit** — `feat(agents): VideoAIAgent on Runway with Ken Burns fallback; remove Kling`.

---

### Task 5: Pipeline wiring, social cuts, CI ffmpeg, frontend label

**Files:**
- Modify: `src/listingjet/pipeline/definition.py` (replace `Step("video", ...)` with `Step("video_baseline", requires=("packaging",), timeout_s=15*_MIN, optional=True)` and `Step("video_ai", requires=("packaging", "await_review"), timeout_s=30*_MIN, optional=True, gate="addon:ai_video_tour")`; `social_cuts` requires `("video_baseline", "video_ai", "await_review")`), `steps.py` (map both agents; drop `VideoAgent`), `runner.py` (`_gated_off`: delete the `step.gate == "video"` branch), `src/listingjet/agents/social_cuts.py` (`ffmpeg_cmd()`, `await asyncio.to_thread(self._cutter.create_cut, ...)` and `to_thread` for storage download/upload; pick the `video_type=="tour"` row first, else latest ready), `.github/workflows/test.yml` (add step `- name: Install ffmpeg` / `run: sudo apt-get update && sudo apt-get install -y ffmpeg` before "Run tests"; `env: FFMPEG_BIN: ffmpeg` not needed), `frontend/src` (grep `ai_generated` and display `"tour"`; `pipeline-status.tsx`/`pipeline-progress.tsx` step lists if they enumerate `video`), `src/listingjet/api/sse.py` + `frontend/src/lib/use-listing-events.ts` (`video.completed` → `video_baseline.completed`, `video_ai.completed`), `api/listings_workflow.py` legacy list (`video` → `video_baseline`)
- Tests: `tests/test_pipeline/test_definition.py` (21 steps; gates; requires), `tests/test_pipeline/test_runner_scale.py` (`video` → `video_baseline`; the parked-listing docstring), `tests/test_pipeline/test_steps.py`, `tests/test_agents/test_social_cuts.py` (cutter still injectable; async), `tests/test_pipeline/test_runner.py` if it tests the `video` gate (replace with `addon:ai_video_tour` cases: credit tenant without addon → `video_ai` SKIPPED, `video_baseline` QUEUED; with addon → both QUEUED).

- [ ] **Step 1: Update tests RED.** - [ ] **Step 2: Implement.** - [ ] **Step 3: Grep gate** `grep -rn "\"video\"\|'video'\|video\.completed\|gate == \"video\"" src tests frontend/src --include=*.py --include=*.ts --include=*.tsx` — inspect each hit; only unrelated strings (e.g. `video_type`, a CSS class) may remain. - [ ] **Step 4: Full suite, ruff, `npx tsc --noEmit`.** - [ ] **Step 5: Commit** — `feat(pipeline): video_baseline + video_ai steps; social cuts off the event loop; ffmpeg in CI`.

---

### Task 6: E2E with mocks, docs, PR

- [ ] Mock e2e as Phase 5 Task 5 (moto :5000, worker, `scripts/seed_sample_listing.py`, approve via `complete_review`), with `FFMPEG_BIN` exported for the worker. Confirm: `video_baseline` `done` before review; after approval `video_ai` `skipped` (seed tenant has no add-on) and `social_cuts` `done`; `video_assets` has one `tour` row with `chapters` and `metadata->>'tier' = 'baseline'`; download `videos/<id>/tour.mp4` from moto and `ffprobe` it (duration ≈ 10×2.5+0.5+5 ≈ 30.5 s, 1920x1080). Then grant the add-on to the seeded tenant (insert an `addon_purchases` row for `ai_video_tour` — check `services/pipeline_start.enabled_addon_slugs` for the exact table/columns) and `/retry` or re-enqueue so `video_ai` runs with `MockRunwayClient`; confirm `tier='ai'`, six `runway_tasks`, and `social_cuts` re-ran. Record timings.
- [ ] `CLAUDE.md`: migration head 056; video row: "ffmpeg Ken Burns baseline + Runway (`gen4_turbo` interiors, `veo3.1_fast` exteriors) add-on". `MASTER_TODO.md`: Phase 5 row `#310`; Phase 6 row `feat/video-two-tier` / PR #, "done, awaiting merge"; carried: remove the Phase 6 chapters item; add "Phase 7: remove `video-upload.tsx` S3 key form if still present"; note "Runway API has no Kling — routing is gen4_turbo/veo3.1_fast; revisit if Runway adds Kling".
- [ ] Full suite 0 failed (with `FFMPEG_BIN` set so the ffmpeg tests run, and report how many `ffmpeg`-marked tests ran), ruff, `alembic heads` = 056, `tsc` clean. Push; `gh pr create --base feat/content-social --title "feat: two-tier video — ffmpeg baseline + Runway add-on (phase 6)"` with body: what replaced what (12 Kling clips ≈ $6 → free baseline + optional 6-shot Runway ≈ $2.20), the Kling-not-on-Runway ruling, resume semantics, fallback, chapters/manifest, 056, CI ffmpeg, e2e evidence, real-provider run pending keys (`RUNWAY_API_KEY`), test summary, merge order `#306 → … → #310 → this`. Attribution lines at the end. Do not merge.

---

## Self-review

- **Spec coverage:** baseline (photos in MLS order, cap 10, non-photo excluded, zoompan 3 s @1080p alternating, xfade 0.5, end card, silent/optional music, `to_thread`, temp cleanup, `videos/{id}/tour.mp4`, `video_type` "tour") ✔ T1+T3. AI add-on (≤6 shots: exterior, drone, 4 interiors; Runway per shot; task ids persisted immediately; semaphore 3; fallback Ken Burns; same stitcher; replaces baseline; per-second cost; `addon:ai_video_tour` for every billing model) ✔ T2+T4+T5 — with the model ruling. Social cuts (`to_thread`, chapters) ✔ T3/T5 (chapters written by both tiers). Tests: stitcher unit tests with generated PNGs, ffmpeg in CI, resume test, old sleep-stagger tests gone with `test_video.py` ✔.
- **Deviation:** spec's Kling routing replaced by `gen4_turbo` (Runway has no Kling); chapters use the frontend's `{time,label}` shape with the richer manifest under `metadata_["clips"]`.
- **Type consistency:** `upsert_tour_asset` (T3→T4), `stitch_xfade(list[tuple[str,float]])` (T1→T3/T4), `record_video_seconds(model_id, seconds, agent)` (T1→T4), `MockRunwayClient.submitted/fail_models` (T2→T4), step names `video_baseline`/`video_ai` (T5, T6).
