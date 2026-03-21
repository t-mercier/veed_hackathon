"""
Multi-scene AI Video Generator
  1. Split narration into intro / steps / outro segments
  2. Generate TTS audio per segment
  3. Calibrate Manim step timing from word count
  4. Render 3 Manim scenes (DijkstraIntro, DijkstraSteps, DijkstraOutro)
  5. Generate avatar pip-in videos for intro + outro (fal.ai Fabric 1.0)
  6. Merge each segment (animation + audio + optional avatar pip-in)
  7. Concat intro | steps | outro → final.mp4
"""

import argparse
import os
import subprocess
import urllib.request
from pathlib import Path

import fal_client
from openai import OpenAI
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
import moviepy.video.fx

# --- Config ---
OPENAI_API_KEY   = os.environ.get("OPENAI_API_KEY")
FAL_KEY          = os.environ.get("FAL_KEY")
AVATAR_IMAGE_URL = os.environ.get(
    "AVATAR_IMAGE_URL",
    "https://v3.fal.media/files/koala/NLVPfOI4XL1cWT2PmmqT3_Hope.png",
)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Narration — split into 3 timed segments
# ---------------------------------------------------------------------------
NARRATION_INTRO = """\
Welcome! Today we're exploring Dijkstra's algorithm — one of the most elegant \
solutions in computer science for finding shortest paths in a weighted graph. \
Here you can see our graph: six nodes, A through F, each edge carrying a travel cost. \
Our goal is to find the cheapest route from A to F.\
"""

NARRATION_STEPS = """\
We begin at node A with a distance of zero. Every other node starts at infinity. \
The rule is simple: always expand the unvisited node with the smallest known distance. \
From A we can reach B at cost four, and C at just two. We visit C first. \
From C we discover a shortcut to B — two plus one equals three, beating the previous four. \
Next we visit B and update D to eight. Then D relaxes F to ten. \
E is reached at twelve, but F is already ten — no update needed. \
All nodes are now visited and every shortest distance is locked in.\
"""

NARRATION_OUTRO = """\
And here is the complete picture. Every shortest distance from A is now known. \
The optimal path to F costs ten: A, then C, then B, then D, then F. \
Dijkstra is correct because it never revisits a node after its shortest distance is settled. \
It runs efficiently in O of V plus E log V time — fast enough for massive real-world networks. \
Whether you are routing network packets, planning a road trip, or solving puzzles, \
this algorithm is your friend.\
"""

# Approximate fixed animation time per Dijkstra step (seconds)
# sum of play() calls in DijkstraSteps, excluding waits
_FIXED_TIME_PER_STEP = 4.2
_N_STEPS = 6


def _word_duration(text: str) -> float:
    """Estimate TTS duration at 130 WPM."""
    return len(text.split()) / 130 * 60


def _compute_step_time(steps_narration: str) -> float:
    """Distribute remaining time (after fixed animations) evenly across steps."""
    target   = _word_duration(steps_narration)
    leftover = target - _FIXED_TIME_PER_STEP * _N_STEPS
    return max(0.8, leftover / _N_STEPS)


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def generate_tts(text: str, out_path: Path) -> Path:
    if not OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY")
    print(f"  [TTS] → {out_path.name}  ({len(text.split())} words)")
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.audio.speech.create(model="tts-1", voice="nova", input=text)
    resp.write_to_file(out_path)
    return out_path


def upload_to_fal(file_path: Path) -> str:
    if not FAL_KEY:
        raise ValueError("Missing FAL_KEY")
    print(f"  [upload] {file_path.name}")
    return fal_client.upload_file(file_path)


def generate_avatar_video(audio_url: str, out_path: Path) -> Path:
    if not FAL_KEY:
        raise ValueError("Missing FAL_KEY")
    print(f"  [avatar] → {out_path.name}")

    def _log(update):
        if hasattr(update, "logs"):
            for lg in update.logs:
                print(f"    [fal] {lg['message']}")

    result = fal_client.subscribe(
        "veed/fabric-1.0",
        arguments={
            "image_url": AVATAR_IMAGE_URL,
            "audio_url": audio_url,
            "resolution": "480p",
        },
        with_logs=True,
        on_queue_update=_log,
    )
    video_url = result["video"]["url"]
    urllib.request.urlretrieve(video_url, out_path)
    return out_path


def render_manim(script_path: Path, scene_name: str, out_dir: Path, env: dict | None = None) -> Path:
    print(f"  [manim] {scene_name}")
    if not script_path.exists():
        raise FileNotFoundError(script_path)

    run_env = {**os.environ, **(env or {})}
    subprocess.run(
        [
            "manim", "-ql",
            "--output_file", scene_name.lower(),
            "--media_dir", str(out_dir / "manim_media"),
            str(script_path), scene_name,
        ],
        check=True,
        env=run_env,
    )

    matches = list((out_dir / "manim_media").rglob(f"{scene_name.lower()}.mp4"))
    if not matches:
        matches = list((out_dir / "manim_media").rglob("*.mp4"))
    if not matches:
        raise FileNotFoundError(f"Manim output not found for {scene_name}")
    return max(matches, key=os.path.getmtime)


def _pip_in_avatar(animation_path: Path, avatar_path: Path, audio_path: Path, out_path: Path) -> Path:
    """Overlay avatar pip-in (bottom-right) on animation, using separate TTS audio as main track."""
    print(f"  [merge] avatar pip-in → {out_path.name}")
    with (
        VideoFileClip(str(animation_path)) as anim,
        VideoFileClip(str(avatar_path))   as av,
        AudioFileClip(str(audio_path))    as aud,
    ):
        # Sync lengths: animation drives the duration
        target_dur = max(anim.duration, aud.duration) + 0.5

        # Scale animation to match audio if needed (pad with freeze)
        av_w  = int(anim.w * 0.22)
        av_rs = av.resized(width=av_w)

        # Loop or trim avatar
        if av_rs.duration < target_dur:
            av_rs = av_rs.with_effects([moviepy.video.fx.Loop(duration=target_dur)])
        else:
            av_rs = av_rs.subclipped(0, target_dur)

        margin = 16
        av_pos = av_rs.with_position(
            (anim.w - av_rs.w - margin, anim.h - av_rs.h - margin)
        )

        anim_padded = anim.subclipped(0, min(anim.duration, target_dur))
        composite   = CompositeVideoClip([anim_padded, av_pos])
        # Replace audio with clean TTS track
        composite   = composite.with_audio(aud.subclipped(0, min(aud.duration, target_dur)))
        composite.write_videofile(str(out_path), codec="libx264", audio_codec="aac")
    return out_path


def _add_audio(animation_path: Path, audio_path: Path, out_path: Path) -> Path:
    """Combine silent Manim animation with TTS audio."""
    print(f"  [merge] audio → {out_path.name}")
    with (
        VideoFileClip(str(animation_path)) as anim,
        AudioFileClip(str(audio_path))     as aud,
    ):
        dur     = max(anim.duration, aud.duration)
        a_clip  = anim.subclipped(0, min(anim.duration, dur))
        au_clip = aud.subclipped(0, min(aud.duration, dur))
        result  = a_clip.with_audio(au_clip)
        result.write_videofile(str(out_path), codec="libx264", audio_codec="aac")
    return out_path


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(output: str = "output/final.mp4"):
    print("\n=== Animated Explainer — Multi-Scene Pipeline ===\n")
    out = OUTPUT_DIR

    # ----- 1. TTS for all 3 segments -----------------------------------
    print("[1/4] Generating TTS audio…")
    audio_intro = generate_tts(NARRATION_INTRO, out / "audio_intro.mp3")
    audio_steps = generate_tts(NARRATION_STEPS, out / "audio_steps.mp3")
    audio_outro = generate_tts(NARRATION_OUTRO, out / "audio_outro.mp3")

    # ----- 2. Avatar videos for intro + outro --------------------------
    print("\n[2/4] Generating avatar videos (intro + outro)…")
    url_intro = upload_to_fal(audio_intro)
    url_outro = upload_to_fal(audio_outro)
    av_intro  = generate_avatar_video(url_intro, out / "avatar_intro.mp4")
    av_outro  = generate_avatar_video(url_outro, out / "avatar_outro.mp4")

    # ----- 3. Render 3 Manim scenes ------------------------------------
    print("\n[3/4] Rendering Manim scenes…")

    step_time  = _compute_step_time(NARRATION_STEPS)
    intro_wait = _word_duration(NARRATION_INTRO) * 0.35   # wait ≈ 35 % of intro duration
    outro_wait = _word_duration(NARRATION_OUTRO) * 0.30

    print(f"  timing: step_time={step_time:.2f}s  intro_wait={intro_wait:.2f}s  outro_wait={outro_wait:.2f}s")

    script = Path("code/explain_dijkstra.py")
    timing_env = {
        "MANIM_STEP_TIME":  str(round(step_time, 3)),
        "MANIM_INTRO_WAIT": str(round(intro_wait, 3)),
        "MANIM_OUTRO_WAIT": str(round(outro_wait, 3)),
    }

    anim_intro = render_manim(script, "DijkstraIntro", out, timing_env)
    anim_steps = render_manim(script, "DijkstraSteps", out, timing_env)
    anim_outro = render_manim(script, "DijkstraOutro", out, timing_env)

    # ----- 4. Merge segments -------------------------------------------
    print("\n[4/4] Merging segments…")
    seg_intro = _pip_in_avatar(anim_intro, av_intro, audio_intro, out / "seg_intro.mp4")
    seg_steps = _add_audio(anim_steps, audio_steps, out / "seg_steps.mp4")
    seg_outro = _pip_in_avatar(anim_outro, av_outro, audio_outro, out / "seg_outro.mp4")

    print("  [concat] all segments → final.mp4")
    clips = [VideoFileClip(str(p)) for p in (seg_intro, seg_steps, seg_outro)]
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(output, codec="libx264", audio_codec="aac")
    for c in clips:
        c.close()
    final.close()

    print(f"\nDone! → {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-scene AI Video Generator")
    parser.add_argument("--output", default="output/final.mp4")
    args = parser.parse_args()
    run(args.output)

