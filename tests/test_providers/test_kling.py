# tests/test_providers/test_kling.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_kling_provider_exists():
    from listingjet.providers.kling import KlingProvider
    assert hasattr(KlingProvider, "generate_clip")
    assert hasattr(KlingProvider, "poll_task")


def test_video_prompts_exist():
    from listingjet.agents.video_template import NEGATIVE_PROMPT, ROOM_CAMERA_CONTROLS, ROOM_PROMPTS
    assert "kitchen" in ROOM_PROMPTS
    assert "living_room" in ROOM_PROMPTS
    assert "exterior" in ROOM_PROMPTS
    assert "kitchen" in ROOM_CAMERA_CONTROLS
    assert "zoom" in ROOM_CAMERA_CONTROLS["kitchen"]
    assert len(NEGATIVE_PROMPT) > 0


def test_standard_60s_template():
    from listingjet.agents.video_template import STANDARD_60S
    assert STANDARD_60S.name == "standard_60s"
    assert STANDARD_60S.clip_duration_s == 5
    assert STANDARD_60S.clip_count == 12
    assert STANDARD_60S.kling_model == "kling-v2-5-turbo"
    assert STANDARD_60S.kling_mode == "pro"
    assert STANDARD_60S.transition == "cut"


def test_kling_jwt_generation():
    from listingjet.providers.kling import KlingProvider
    provider = KlingProvider(access_key="test_ak", secret_key="test_sk")
    token = provider._generate_jwt()
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
@patch("listingjet.providers.kling.httpx.AsyncClient")
async def test_kling_generate_clip_submits_task(MockClient):
    from listingjet.providers.kling import KlingProvider

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 0, "data": {"task_id": "task_123"}}

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    MockClient.return_value = mock_client_instance

    provider = KlingProvider(access_key="test_ak", secret_key="test_sk")
    task_id = await provider.generate_clip(
        image_url="https://example.com/photo.jpg",
        prompt="Slow cinematic dolly into kitchen",
        negative_prompt="shaky camera",
        camera_control={"zoom": 5, "horizontal": 0},
    )
    assert task_id == "task_123"


@pytest.mark.asyncio
@patch("listingjet.providers.kling.httpx.AsyncClient")
async def test_kling_poll_task_returns_url(MockClient):
    from listingjet.providers.kling import KlingProvider

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 0,
        "data": {
            "task_status": "succeed",
            "task_result": {"videos": [{"url": "https://cdn.kling.ai/video.mp4", "duration": "5"}]},
        },
    }

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    MockClient.return_value = mock_client_instance

    provider = KlingProvider(access_key="test_ak", secret_key="test_sk")
    result = await provider.poll_task("task_123", timeout=10, interval=1)
    assert result == {"url": "https://cdn.kling.ai/video.mp4", "duration": "5", "credits": None}
