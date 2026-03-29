"""ElevenLabs text-to-speech provider for property tour voiceovers.

Converts Claude-generated property descriptions into professional narration
audio that can be overlaid on tour videos.

Uses the Turbo v2.5 model for sub-second latency and lower cost (~$0.12/1k chars).
"""
import logging
from abc import ABC, abstractmethod

import httpx

from listingjet.config import settings

logger = logging.getLogger(__name__)

_API_BASE = "https://api.elevenlabs.io/v1"

# Professional real estate narration voice
_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" — warm, professional
_DEFAULT_MODEL = "eleven_turbo_v2_5"


class VoiceoverProvider(ABC):
    """Abstract base for text-to-speech providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """Convert text to speech audio. Returns MP3 bytes."""
        ...


class ElevenLabsProvider(VoiceoverProvider):
    """ElevenLabs TTS for property tour narration."""

    def __init__(self, api_key: str | None = None, voice_id: str | None = None):
        self._api_key = api_key or settings.elevenlabs_api_key
        self._voice_id = voice_id or _DEFAULT_VOICE_ID

    async def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """Generate speech from text. Returns MP3 bytes."""
        vid = voice_id or self._voice_id

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_API_BASE}/text-to-speech/{vid}",
                headers={
                    "xi-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": _DEFAULT_MODEL,
                    "voice_settings": {
                        "stability": 0.6,
                        "similarity_boost": 0.8,
                        "style": 0.3,
                    },
                },
            )
            resp.raise_for_status()
            return resp.content


class MockVoiceoverProvider(VoiceoverProvider):
    """Mock provider for testing — returns empty MP3 bytes."""

    async def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        return b""


def get_voiceover_provider() -> VoiceoverProvider:
    if settings.use_mock_providers or not getattr(settings, "elevenlabs_api_key", ""):
        return MockVoiceoverProvider()
    return ElevenLabsProvider()
