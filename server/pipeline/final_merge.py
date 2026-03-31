"""
Final video assembly using ffmpeg.

Layout:
  1. intro.mp4          — avatar talking head (full screen)
  2. animation.mp4      — Manim animation with info.mp3 audio overlaid
  3. outro.mp4          — avatar talking head (full screen)

All segments are scaled to 854x480 before concatenation.
"""

import subprocess
import tempfile
from pathlib import Path


_SCALE = "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2"


def _run(*args: str) -> None:
    subprocess.run(list(args), check=True, capture_output=True, close_fds=True, stdin=subprocess.DEVNULL)


def merge_final(
    intro_path: Path,
    animation_path: Path,
    info_audio_path: Path,
    outro_path: Path,
    out_path: Path,
) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)

        # Scale intro to 854x480
        intro_scaled = t / "intro_scaled.mp4"
        _run(
            "ffmpeg", "-y",
            "-i", str(intro_path),
            "-vf", _SCALE,
            "-c:v", "libx264", "-c:a", "aac",
            str(intro_scaled),
        )

        # Overlay info.mp3 audio onto animation.mp4 and scale
        anim_with_audio = t / "anim_audio.mp4"
        _run(
            "ffmpeg", "-y",
            "-i", str(animation_path),
            "-i", str(info_audio_path),
            "-vf", _SCALE,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(anim_with_audio),
        )

        # Scale outro to 854x480
        outro_scaled = t / "outro_scaled.mp4"
        _run(
            "ffmpeg", "-y",
            "-i", str(outro_path),
            "-vf", _SCALE,
            "-c:v", "libx264", "-c:a", "aac",
            str(outro_scaled),
        )

        # Concat list file
        concat_list = t / "concat.txt"
        concat_list.write_text(
            f"file '{intro_scaled}'\nfile '{anim_with_audio}'\nfile '{outro_scaled}'\n"
        )

        _run(
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(out_path),
        )

    return out_path
