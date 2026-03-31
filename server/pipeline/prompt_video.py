"""
Renders a final.mp4 for repo/prompt-mode jobs.

Structure:
  intro.mp4  →  [scene_0 card + audio]  →  …  →  [scene_N card + audio]  →  outro.mp4

Each scene card: dark background + scene title + bullet points + scene narration audio.
Falls back to info.mp3 over dark bg if no storyboard/scene audio found.
"""

import json
import logging
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

W, H = 854, 480
BG      = (15, 23, 42)        # #0F172A
WHITE   = (255, 255, 255)
GRAY    = (148, 163, 184)     # slate-400
ACCENT  = (96, 165, 250)      # blue-400
FONT    = "/System/Library/Fonts/HelveticaNeue.ttc"
SCALE_F = "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2,setsar=1"


def _run(*args: str) -> None:
    subprocess.run(list(args), check=True, capture_output=True,
                   close_fds=True, stdin=subprocess.DEVNULL)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT, size, index=1 if bold else 0)
    except Exception:
        return ImageFont.load_default()


def _audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True, text=True
    )
    try:
        for s in json.loads(result.stdout).get("streams", []):
            if "duration" in s:
                return float(s["duration"])
    except Exception:
        pass
    return 5.0


def _make_card(title: str, bullets: list[str], out_png: Path) -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W, 4)], fill=ACCENT)

    ft = _font(36, bold=True)
    fb = _font(22)

    y = 80
    for line in textwrap.wrap(title, width=50)[:2]:
        bbox = draw.textbbox((0, 0), line, font=ft)
        draw.text(((W - (bbox[2] - bbox[0])) // 2, y), line, font=ft, fill=WHITE)
        y += 48

    y += 16
    draw.rectangle([(W // 2 - 120, y), (W // 2 + 120, y + 2)], fill=ACCENT)
    y += 24

    for bullet in bullets[:3]:
        lines = textwrap.wrap(bullet, width=60)
        text = (lines[0] + "…") if len(lines) > 1 else (lines[0] if lines else bullet)
        draw.ellipse([(W // 2 - 200, y + 8), (W // 2 - 192, y + 16)], fill=ACCENT)
        draw.text((W // 2 - 184, y), text, font=fb, fill=GRAY)
        y += 40

    img.save(str(out_png))


def _card_to_video(png: Path, audio: Path, out: Path) -> None:
    duration = _audio_duration(audio) + 0.5
    _run(
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration), "-i", str(png),
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-vf", f"scale={W}:{H},setsar=1",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(out),
    )


def _scale_avatar(src: Path, out: Path) -> None:
    _run(
        "ffmpeg", "-y", "-i", str(src),
        "-vf", SCALE_F,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(out),
    )


def _dark_audio_video(audio: Path, out: Path) -> None:
    _run(
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#0f172a:size={W}x{H}:rate=24",
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(out),
    )


def render_prompt_video(job_dir: Path) -> Path:
    intro  = job_dir / "intro.mp4"
    outro  = job_dir / "outro.mp4"
    out    = job_dir / "final.mp4"

    if not intro.exists() or not outro.exists():
        raise FileNotFoundError(f"Missing intro.mp4 or outro.mp4 in {job_dir}")

    # --- Build middle segments from scenes ---
    middle: list[Path] = []

    storyboard_path = job_dir / "storyboard.json"
    if storyboard_path.exists():
        storyboard = json.loads(storyboard_path.read_text())
        scenes = storyboard.get("scenes", [])
        for i, scene in enumerate(scenes):
            audio = job_dir / f"scene_{i}.mp3"
            if not audio.exists():
                continue
            title   = scene.get("title", f"Scene {i + 1}")
            bullets = scene.get("panel", {}).get("bullets", [])
            png = job_dir / f"_card_{i}.png"
            mp4 = job_dir / f"_scene_{i}.mp4"
            logger.info("Scene card %d/%d: %s", i + 1, len(scenes), title)
            _make_card(title, bullets, png)
            _card_to_video(png, audio, mp4)
            middle.append(mp4)

    # fallback: single dark screen with info.mp3
    if not middle:
        info = job_dir / "info.mp3"
        if info.exists():
            dark = job_dir / "_info_dark.mp4"
            logger.info("No scene cards — using info.mp3 over dark bg")
            _dark_audio_video(info, dark)
            middle.append(dark)

    if not middle:
        raise FileNotFoundError("No scene audio or info.mp3 found")

    # --- Scale intro / outro ---
    intro_s = job_dir / "_intro_s.mp4"
    outro_s = job_dir / "_outro_s.mp4"
    logger.info("Scaling intro/outro…")
    _scale_avatar(intro, intro_s)
    _scale_avatar(outro, outro_s)

    # --- Concat ---
    segments = [intro_s] + middle + [outro_s]
    concat_f = job_dir / "_concat.txt"
    concat_f.write_text("\n".join(f"file '{p.resolve()}'" for p in segments))

    logger.info("Concatenating %d segments → final.mp4", len(segments))
    _run(
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_f),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(out),
    )

    logger.info("Done → %s", out)
    return out
