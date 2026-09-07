"""Tests for endcard generation service."""
import pytest

from listingjet.services.endcard import ENDCARD_DURATION, endcard_clip, generate_endcard
from listingjet.services.video_stitcher import probe_duration


def test_generate_endcard_returns_png_bytes():
    result = generate_endcard(brokerage_name="Acme Realty", agent_name="John Doe")
    assert isinstance(result, bytes)
    assert len(result) > 100
    # PNG magic bytes
    assert result[:4] == b"\x89PNG"


def test_generate_endcard_default_params():
    result = generate_endcard()
    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_generate_endcard_with_custom_color():
    result = generate_endcard(primary_color="#FF5500", agent_name="Jane")
    assert isinstance(result, bytes)
    assert len(result) > 100


@pytest.mark.ffmpeg
def test_endcard_clip_has_requested_duration(ffmpeg_available, tmp_path):
    png = generate_endcard(brokerage_name="Acme Realty", agent_name="John Doe")
    out = endcard_clip(png, str(tmp_path / "endcard.mp4"), duration_s=2.0, width=320, height=180)
    assert abs(probe_duration(out) - 2.0) < 0.15


@pytest.mark.ffmpeg
def test_endcard_clip_default_duration(ffmpeg_available, tmp_path):
    png = generate_endcard()
    out = endcard_clip(png, str(tmp_path / "endcard.mp4"), width=320, height=180)
    assert abs(probe_duration(out) - ENDCARD_DURATION) < 0.15
