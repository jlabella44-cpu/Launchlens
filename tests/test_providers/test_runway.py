"""Tests for the Runway image-to-video client.

RunwayClient is the single place that talks to Runway's Dev API
(/v1/image_to_video + /v1/tasks/{id}) via raw httpx (no `runwayml` SDK
dependency). See test_openai_images.py for the house style this mirrors.
"""
from unittest.mock import AsyncMock

import pytest
from pytest_httpx import HTTPXMock

from listingjet.providers.mock import MockRunwayClient
from listingjet.providers.runway import RunwayClient, RunwayError, RunwayTaskFailed


@pytest.mark.asyncio
async def test_image_to_video_posts_expected_body_and_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.dev.runwayml.com/v1/image_to_video",
        json={"id": "t1"},
    )

    client = RunwayClient(api_key="k")
    task_id = await client.image_to_video(
        "https://s3.example.com/photo.jpg",
        "slow pan across the living room",
        model="gen4_turbo",
        duration=5,
        ratio="1280:720",
    )
    assert task_id == "t1"

    req = httpx_mock.get_request(url="https://api.dev.runwayml.com/v1/image_to_video")
    assert req is not None
    assert req.headers["authorization"] == "Bearer k"
    assert req.headers["x-runway-version"] == "2024-11-06"
    import json

    body = json.loads(req.content)
    assert body["model"] == "gen4_turbo"
    assert body["promptImage"] == "https://s3.example.com/photo.jpg"
    assert body["promptText"] == "slow pan across the living room"
    assert body["duration"] == 5
    assert body["ratio"] == "1280:720"
    assert "audio" not in body

    await client.aclose()


@pytest.mark.asyncio
async def test_image_to_video_truncates_prompt_to_1000_chars(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.dev.runwayml.com/v1/image_to_video",
        json={"id": "t1"},
    )

    client = RunwayClient(api_key="k")
    await client.image_to_video(
        "https://s3.example.com/photo.jpg", "x" * 1500, model="gen4_turbo", duration=5,
    )

    import json

    body = json.loads(httpx_mock.get_request(
        url="https://api.dev.runwayml.com/v1/image_to_video"
    ).content)
    assert body["promptText"] == "x" * 1000

    await client.aclose()


@pytest.mark.asyncio
async def test_image_to_video_includes_audio_when_passed(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.dev.runwayml.com/v1/image_to_video",
        json={"id": "t1"},
    )

    client = RunwayClient(api_key="k")
    await client.image_to_video(
        "https://s3.example.com/photo.jpg",
        "prompt",
        model="veo3.1_fast",
        duration=5,
        audio=False,
    )

    req = httpx_mock.get_request(url="https://api.dev.runwayml.com/v1/image_to_video")
    import json

    body = json.loads(req.content)
    assert body["audio"] is False

    await client.aclose()


@pytest.mark.asyncio
async def test_image_to_video_raises_on_400_with_no_retry(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.dev.runwayml.com/v1/image_to_video",
        status_code=400,
        text="bad promptImage",
    )

    client = RunwayClient(api_key="k")
    with pytest.raises(RunwayError) as exc_info:
        await client.image_to_video(
            "https://s3.example.com/photo.jpg", "prompt", model="gen4_turbo", duration=5,
        )
    assert "bad promptImage" in str(exc_info.value)
    assert len(httpx_mock.get_requests()) == 1

    await client.aclose()


@pytest.mark.asyncio
async def test_wait_polls_until_succeeded(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setattr("listingjet.providers.runway.asyncio.sleep", AsyncMock())

    httpx_mock.add_response(
        method="GET",
        url="https://api.dev.runwayml.com/v1/tasks/t1",
        json={"status": "PENDING"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.dev.runwayml.com/v1/tasks/t1",
        json={"status": "RUNNING"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.dev.runwayml.com/v1/tasks/t1",
        json={"status": "SUCCEEDED", "output": ["https://cdn/x.mp4"]},
    )

    client = RunwayClient(api_key="k")
    result = await client.wait("t1")
    assert result == ["https://cdn/x.mp4"]

    await client.aclose()


@pytest.mark.asyncio
async def test_wait_raises_runway_task_failed_with_failure_code(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setattr("listingjet.providers.runway.asyncio.sleep", AsyncMock())

    httpx_mock.add_response(
        method="GET",
        url="https://api.dev.runwayml.com/v1/tasks/t1",
        json={"status": "FAILED", "failure": "content flagged", "failureCode": "SAFETY"},
    )

    client = RunwayClient(api_key="k")
    with pytest.raises(RunwayTaskFailed) as exc_info:
        await client.wait("t1")
    assert exc_info.value.task_id == "t1"
    assert exc_info.value.failure_code == "SAFETY"

    await client.aclose()


@pytest.mark.asyncio
async def test_wait_raises_runway_error_on_timeout(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setattr("listingjet.providers.runway.asyncio.sleep", AsyncMock())

    httpx_mock.add_response(
        method="GET",
        url="https://api.dev.runwayml.com/v1/tasks/t1",
        json={"status": "PENDING"},
    )

    client = RunwayClient(api_key="k")
    with pytest.raises(RunwayError):
        await client.wait("t1", timeout_s=0)

    await client.aclose()


@pytest.mark.ffmpeg
@pytest.mark.asyncio
async def test_mock_runway_download_returns_playable_clip(ffmpeg_available):
    import tempfile
    from pathlib import Path

    from listingjet.services.video_stitcher import probe_duration

    client = MockRunwayClient()
    data = await client.download("mock://clip/mock-task-1")
    assert len(data) > 0

    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "out.mp4")
        Path(path).write_bytes(data)
        duration = probe_duration(path)
    assert duration == pytest.approx(2.0, abs=0.3)
