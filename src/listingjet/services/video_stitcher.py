"""FFmpeg-based video stitcher with transitions and music overlay.
Ported from Juke Marketing Engine.

Also provides ffmpeg Ken Burns / xfade primitives for the two-tier video
pipeline (Task 1, Phase 6): per-image pan/zoom clips (`build_ken_burns_clip`),
static clips (`build_still_clip`), and crossfade stitching (`VideoStitcher.stitch_xfade`).
"""

import json
import os
import subprocess
import tempfile

from listingjet.config import settings


def ffmpeg_cmd() -> str:
    return settings.ffmpeg_bin


def ffprobe_cmd() -> str:
    head, tail = os.path.split(settings.ffmpeg_bin)
    probe_tail = tail.replace("ffmpeg", "ffprobe", 1)
    return f"{head}/{probe_tail}" if head else probe_tail


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

    def stitch(
        self,
        clip_paths: list[str],
        transitions: list[str],
        music_path: str | None = None,
        output_width: int = 1280,
        output_height: int = 720,
    ) -> bytes:
        """Stitch clips into a single video with transitions and optional music.
        Returns the final video as bytes.
        """
        if not clip_paths:
            raise ValueError("No clips to stitch")

        if len(clip_paths) == 1:
            with open(clip_paths[0], "rb") as f:
                return f.read()

        # Hard-cut path: when all transitions are "cut" (or none provided),
        # re-encode via concat filter for uniform output (clips may differ in codec/res).
        if not transitions or all(t == "cut" for t in transitions):
            return self._stitch_hard_cuts(clip_paths, output_width, output_height)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.mp4")

            # Build FFmpeg filter graph with xfade transitions
            inputs = []
            for clip in clip_paths:
                inputs.extend(["-i", clip])

            filter_parts = []
            # Normalize all clips
            for i in range(len(clip_paths)):
                filter_parts.append(
                    f"[{i}:v]scale={output_width}:{output_height}:force_original_aspect_ratio=decrease,"
                    f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                )

            # Chain xfade transitions
            prev = "v0"
            for i in range(1, len(clip_paths)):
                transition = transitions[i - 1] if i - 1 < len(transitions) else "fade"
                offset = i * 5 - self._transition_duration * i  # 5s per clip minus overlap
                out = f"xf{i}"
                filter_parts.append(
                    f"[{prev}][v{i}]xfade=transition={transition}:duration={self._transition_duration}:offset={offset:.1f}[{out}];"
                )
                prev = out

            filter_graph = "".join(filter_parts).rstrip(";")

            cmd = [ffmpeg_cmd(), "-y"] + inputs + [
                "-filter_complex", filter_graph,
                "-map", f"[{prev}]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
            ]

            # Add music if provided
            if music_path and os.path.exists(music_path):
                cmd.extend([
                    "-i", music_path,
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-shortest",
                ])

            cmd.extend([output_path])

            subprocess.run(cmd, capture_output=True, check=True)

            with open(output_path, "rb") as f:
                return f.read()

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

    def _stitch_hard_cuts(
        self,
        clip_paths: list[str],
        output_width: int,
        output_height: int,
    ) -> bytes:
        """Stitch clips with hard cuts via two-pass approach.

        Pass 1: Normalize each clip to uniform resolution/fps/codec (one at a time).
        Pass 2: Concat demuxer joins normalized files (stream-copy, near-zero memory).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pass 1: normalize each clip individually
            normalized = []
            for i, clip in enumerate(clip_paths):
                norm_path = os.path.join(tmpdir, f"norm_{i}.mp4")
                subprocess.run([
                    ffmpeg_cmd(), "-y", "-i", clip,
                    "-vf", f"scale={output_width}:{output_height}:force_original_aspect_ratio=decrease,"
                           f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-an",
                    norm_path,
                ], capture_output=True, check=True)
                normalized.append(norm_path)

            # Pass 2: concat demuxer (stream-copy, minimal memory)
            concat_list = os.path.join(tmpdir, "concat.txt")
            with open(concat_list, "w") as f:
                for path in normalized:
                    f.write(f"file '{path}'\n")

            output_path = os.path.join(tmpdir, "output.mp4")
            subprocess.run([
                ffmpeg_cmd(), "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c", "copy", output_path,
            ], capture_output=True, check=True)

            with open(output_path, "rb") as f:
                return f.read()
