"""
Bote's VEED pipeline — clean async wrapper for the server.

Given a TTSScript and job output dir:
  1. Runware TTS → intro.mp3, info.mp3, outro.mp3
  2. fal.ai (VEED Fabric 1.0) → intro.mp4, outro.mp4 (talking-head avatar)

Returns paths to the 4 output files.
"""

import asyncio
import base64
import logging
import os
import shutil as _shutil
import subprocess as _subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests as _requests
import fal_client
from runware import Runware, IAudioInference, IAudioSpeech

from config import settings

logger = logging.getLogger(__name__)

_FFMPEG = _shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


@dataclass
class VeedResult:
    intro_video: Path
    info_audio: Path
    outro_video: Path


async def _apply_robotic(path: Path) -> None:
    """Lower pitch ~3 semitones + boost 3kHz — applied in-place.
    Runs ffmpeg in a thread pool to avoid SIGTTOU in background server processes."""
    tmp = path.with_suffix(".robotic.mp3")

    def _run() -> int:
        result = _subprocess.run(
            [_FFMPEG, "-y", "-i", str(path),
             "-af", "asetrate=44100*1.08,aresample=44100,highpass=f=500,equalizer=f=3500:width_type=o:width=2:g=5",
             str(tmp)],
            stdin=_subprocess.DEVNULL,
            stdout=_subprocess.DEVNULL,
            stderr=_subprocess.DEVNULL,
            close_fds=True,
        )
        return result.returncode

    loop = asyncio.get_event_loop()
    rc = await loop.run_in_executor(None, _run)
    if rc == 0:
        tmp.replace(path)
    else:
        logger.warning("ffmpeg robotic post-processing failed (rc=%d) — using plain TTS", rc)
        tmp.unlink(missing_ok=True)


async def _tts(text: str, out_path: Path, voice: str = "Oliver", robotic: bool = False) -> Path:
    """Runware TTS → mp3 file. If robotic=True, applies pitch-shift post-processing via ffmpeg."""
    runware = Runware(api_key=settings.runware_api_key)
    await runware.connect()
    try:
        results = await runware.audioInference(
            requestAudio=IAudioInference(
                model="inworld:tts@1.5-mini",
                speech=IAudioSpeech(text=text, voice=voice),
            )
        )
        audio = results[0]
        if audio.audioURL:
            resp = _requests.get(audio.audioURL)
            out_path.write_bytes(resp.content)
        elif audio.audioBase64Data:
            out_path.write_bytes(base64.b64decode(audio.audioBase64Data))
        else:
            raise RuntimeError("Runware returned no audio data")
    finally:
        await runware.disconnect()

    if robotic:
        await _apply_robotic(out_path)

    return out_path


async def generate_tts_audio(text: str, out_path: Path, voice: str = "Oliver", robotic: bool = False) -> Path:
    """Public wrapper for TTS generation — used by repo pipeline for per-scene audio."""
    if not settings.runware_api_key:
        raise RuntimeError("RUNWARE_API_KEY is not set")
    return await _tts(text, out_path, voice=voice, robotic=robotic)


async def _avatar_video(audio_path: Path, out_path: Path, image_url: Optional[str] = None) -> Path:
    """fal.ai VEED Fabric 1.0: audio + avatar image → mp4 URL → downloaded file."""
    os.environ["FAL_KEY"] = settings.fal_key

    audio_url = fal_client.upload_file(str(audio_path))
    image_url = image_url or settings.avatar_image_url

    result = fal_client.run(
        "veed/fabric-1.0",
        arguments={
            "image_url": image_url,
            "audio_url": audio_url,
            "resolution": "480p",
        },
    )
    video_url = result["video"]["url"]
    resp = _requests.get(video_url)
    out_path.write_bytes(resp.content)
    return out_path


async def run_veed_pipeline(
    intro_text: str,
    info_text: str,
    outro_text: str,
    job_dir: Path,
    avatar_image_url: Optional[str] = None,
    voice: str = "Oliver",
    robotic: bool = False,
) -> VeedResult:
    """
    Full Bote pipeline for one job.
    Generates 3 TTS audio files and 2 avatar videos (intro + outro).
    """
    if not settings.runware_api_key:
        raise RuntimeError("RUNWARE_API_KEY is not set")
    if not settings.fal_key:
        raise RuntimeError("FAL_KEY is not set")

    intro_mp3 = job_dir / "intro.mp3"
    info_mp3 = job_dir / "info.mp3"
    outro_mp3 = job_dir / "outro.mp3"

    logger.info("Generating TTS audio (intro + info + outro) voice=%s robotic=%s…", voice, robotic)
    await asyncio.gather(
        _tts(intro_text, intro_mp3, voice=voice, robotic=robotic),
        _tts(info_text, info_mp3, voice=voice, robotic=robotic),
        _tts(outro_text, outro_mp3, voice=voice, robotic=robotic),
    )

    logger.info("Generating avatar videos (intro + outro) — image: %s", avatar_image_url or "default")
    intro_mp4 = job_dir / "intro.mp4"
    outro_mp4 = job_dir / "outro.mp4"
    await asyncio.gather(
        _avatar_video(intro_mp3, intro_mp4, image_url=avatar_image_url),
        _avatar_video(outro_mp3, outro_mp4, image_url=avatar_image_url),
    )

    return VeedResult(
        intro_video=intro_mp4,
        info_audio=info_mp3,
        outro_video=outro_mp4,
    )
