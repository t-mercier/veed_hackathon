"""
MVP Pipeline — AI Video Generator
Steps:
  1. Generate TTS audio (OpenAI)
  2. Upload audio to fal.ai storage
  3. fal.ai Fabric 1.0: avatar image + audio → avatar.mp4
  4. Manim: render animation.mp4
  5. moviepy: merge animation + avatar (pip) → final.mp4
"""

import os
import subprocess
import tempfile
from pathlib import Path

import fal_client
from openai import OpenAI
from moviepy.editor import VideoFileClip, CompositeVideoClip

# --- Config ---
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
FAL_KEY = os.environ["FAL_KEY"]

AVATAR_IMAGE_URL = (
    "https://v3.fal.media/files/koala/NLVPfOI4XL1cWT2PmmqT3_Hope.png"  # default; override via env
)
AVATAR_IMAGE_URL = os.environ.get("AVATAR_IMAGE_URL", AVATAR_IMAGE_URL)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

NARRATION = """
Welcome! Today we're exploring Dijkstra's algorithm — one of the most elegant solutions in computer science.

Dijkstra solves a simple question: what is the shortest path between two nodes in a weighted graph?

We start at node A with a distance of zero. All other nodes begin at infinity.

At each step, we visit the unvisited node with the smallest known distance.
From node A, we can reach B at cost 4, and C at cost 2. C is closer, so we visit it first.

From C, we find a shorter path to B: 2 plus 1 equals 3. Better than 4, so we update.

We continue until all reachable nodes are visited.

The result: the shortest path from A to F costs 10, following A → C → B → D → F.

That's Dijkstra — greedy, correct, and fast.
"""


def generate_tts(text: str, out_path: Path) -> Path:
    print("[1/5] Generating TTS audio...")
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
    )
    response.stream_to_file(out_path)
    print(f"      Saved: {out_path}")
    return out_path


def upload_to_fal(file_path: Path) -> str:
    print("[2/5] Uploading audio to fal.ai...")
    url = fal_client.upload_file(str(file_path))
    print(f"      URL: {url}")
    return url


def generate_avatar_video(audio_url: str, out_path: Path) -> Path:
    print("[3/5] Generating avatar video via Fabric 1.0...")

    def on_queue_update(update):
        if hasattr(update, "logs"):
            for log in update.logs:
                print(f"      [fal] {log['message']}")

    result = fal_client.subscribe(
        "veed/fabric-1.0",
        arguments={
            "image_url": AVATAR_IMAGE_URL,
            "audio_url": audio_url,
            "resolution": "480p",
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    video_url = result["video"]["url"]
    print(f"      Avatar video URL: {video_url}")

    import urllib.request
    urllib.request.urlretrieve(video_url, out_path)
    print(f"      Saved: {out_path}")
    return out_path


def render_manim(out_dir: Path) -> Path:
    print("[4/5] Rendering Manim animation...")
    script = Path(__file__).parent / "code" / "explain_dijkstra.py"
    cmd = [
        "manim",
        "-ql",           # low quality for fast render; change to -qh for high
        "--output_file", "animation",
        "--media_dir", str(out_dir / "manim_media"),
        str(script),
        "DijkstraScene",
    ]
    subprocess.run(cmd, check=True)

    # Manim outputs to media/videos/<script>/<quality>/animation.mp4
    matches = list((out_dir / "manim_media").rglob("animation.mp4"))
    if not matches:
        raise FileNotFoundError("Manim output not found.")
    print(f"      Found: {matches[0]}")
    return matches[0]


def merge_videos(animation_path: Path, avatar_path: Path, out_path: Path) -> Path:
    print("[5/5] Merging videos with moviepy...")

    animation = VideoFileClip(str(animation_path))
    avatar = VideoFileClip(str(avatar_path))

    # Scale avatar to ~25% of animation width, place bottom-right
    avatar_w = int(animation.w * 0.25)
    avatar_h = int(avatar.h * (avatar_w / avatar.w))
    avatar_resized = avatar.resize((avatar_w, avatar_h))

    margin = 20
    avatar_positioned = avatar_resized.set_position(
        (animation.w - avatar_w - margin, animation.h - avatar_h - margin)
    )

    # Loop avatar if shorter than animation, trim if longer
    if avatar_resized.duration < animation.duration:
        avatar_positioned = avatar_positioned.loop(duration=animation.duration)
    else:
        avatar_positioned = avatar_positioned.subclip(0, animation.duration)

    composite = CompositeVideoClip([animation, avatar_positioned])
    composite.write_videofile(str(out_path), codec="libx264", audio_codec="aac")

    print(f"      Final video: {out_path}")
    return out_path


def run():
    audio_path = OUTPUT_DIR / "narration.mp3"
    avatar_path = OUTPUT_DIR / "avatar.mp4"
    final_path = OUTPUT_DIR / "final.mp4"

    generate_tts(NARRATION, audio_path)
    audio_url = upload_to_fal(audio_path)
    generate_avatar_video(audio_url, avatar_path)
    animation_path = render_manim(OUTPUT_DIR)
    merge_videos(animation_path, avatar_path, final_path)

    print(f"\nDone! Output: {final_path}")


if __name__ == "__main__":
    run()
