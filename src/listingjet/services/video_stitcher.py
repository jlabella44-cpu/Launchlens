"""FFmpeg-based video stitcher with transitions and music overlay.
Ported from Juke Marketing Engine.
"""

import os
import subprocess
import tempfile


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

            cmd = ["ffmpeg", "-y"] + inputs + [
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

    def _stitch_hard_cuts(
        self,
        clip_paths: list[str],
        output_width: int,
        output_height: int,
    ) -> bytes:
        """Stitch clips with hard cuts (no transitions) via ffmpeg concat filter.

        Re-encodes to normalize resolution/fps across heterogeneous clips
        (Kling clips + endcard rendered at different sizes).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.mp4")

            inputs = []
            for clip in clip_paths:
                inputs.extend(["-i", clip])

            filter_parts = []
            for i in range(len(clip_paths)):
                filter_parts.append(
                    f"[{i}:v]scale={output_width}:{output_height}:force_original_aspect_ratio=decrease,"
                    f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                )
            concat_inputs = "".join(f"[v{i}]" for i in range(len(clip_paths)))
            filter_parts.append(f"{concat_inputs}concat=n={len(clip_paths)}:v=1:a=0[out]")
            filter_graph = "".join(filter_parts)

            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_graph,
                "-map", "[out]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            with open(output_path, "rb") as f:
                return f.read()
