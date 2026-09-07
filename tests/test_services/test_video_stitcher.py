import os

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
