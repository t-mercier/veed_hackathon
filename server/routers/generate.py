"""
Generate endpoint — main entry point for both explanation flows.

POST /generate   → starts background pipeline, returns job_id immediately
GET  /jobs/{id}  → poll for status, progress, results

Three pipelines:
  - Repo path:          GitHub URL → repo analysis → storyboard → narration (React Flow on frontend)
  - Prompt/code path:   code/concept prompt → structured explanation → storyboard → narration (scene renderer on frontend)
  - Concept/algo path:  concept prompt → single-scene Manim animation (Premium)
"""

import asyncio
import json
import logging
import shutil
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse

from models import GenerateRequest, JobResponse, JobStatus, JobType, TTSScriptResponse
from pipeline.enrich import enrich_prompt, ingest_github_repo
from pipeline.veed_pipeline import run_veed_pipeline, generate_tts_audio, _tts
from pipeline.repo_analysis import analyze_repo
from pipeline.repo_storyboard import generate_storyboard
from pipeline.repo_narration import assemble_narration, narration_to_tts_info
from pipeline.prompt_analysis import analyze_prompt, classify_prompt
from pipeline.prompt_storyboard import generate_prompt_storyboard
from pipeline.prompt_narration import assemble_prompt_narration, narration_to_tts_info as prompt_narration_to_tts_info
from pipeline.concept_manim import generate_concept_manim
from pipeline.manim_render import render_manim
from pipeline.final_merge import merge_final
from database import job_dir
from config import settings
from supabase_client import update_request_status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])

_jobs: dict[str, dict] = {}

# Avatar ID → fal.ai CDN URLs (uploaded once, permanent)
AVATAR_IMAGES: dict[str, str] = {
    "c3po": "https://v3b.fal.media/files/b/0a931d8c/59Vm9dNdvoQGycZoi-yjA_c3po.jpg",
    "super_man": "https://v3b.fal.media/files/b/0a931d8c/NifMgAk4qThucrr6DxfhQ_super_man.jpg",
    "wonder_woman": "https://v3b.fal.media/files/b/0a931d8c/EnlJgbO2QVvUMcMBTqajh_wonder_woman.jpg",
}

# Avatar ID → Runware TTS voice — matched to persona
AVATAR_VOICES: dict[str, str] = {
    "c3po": "Rupert",        # formal British — robot protocol officer
    "super_man": "Sebastian", # strong confident male — hero
    "wonder_woman": "Victoria", # powerful regal female — warrior queen
}


def _set(job_id: str, **kwargs):
    _jobs[job_id].update(kwargs)


@router.post("/generate", response_model=JobResponse, status_code=202)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks, request: Request):
    job_id = str(uuid.uuid4())
    base_url = str(request.base_url).rstrip("/")
    _jobs[job_id] = {
        "status": JobStatus.pending,
        "progress": "Queued",
        "job_type": None,
        "animation_url": None,
        "final_url": None,
        "architecture": None,
        "storyboard": None,
        "narration": None,
        "explanation": None,
        "tts_script": None,
        "error": None,
    }
    background_tasks.add_task(_run_pipeline, job_id, req, base_url)
    return JobResponse(job_id=job_id, status=JobStatus.pending, progress="Queued")


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(job_id=job_id, **job)


@router.get("/download/{job_id}")
async def download_video(job_id: str):
    """Download the generated Manim video (concept_algo jobs only)."""
    out_dir = job_dir(job_id)
    for name in ("final.mp4", "animation.mp4"):
        p = out_dir / name
        if p.exists():
            return FileResponse(p, media_type="video/mp4",
                                filename=f"explainer-{job_id[:8]}.mp4")
    raise HTTPException(status_code=404, detail="No video file found for this job")


@router.get("/preview-voice/{voice}")
async def preview_voice(voice: str, robotic: bool = False):
    """Generate a short TTS clip for a voice and return it as audio/mpeg."""
    import io
    import tempfile
    from fastapi.responses import StreamingResponse

    sample_text = f"Hello, I'm {voice}. I'll be your AI presenter today."
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        await _tts(sample_text, tmp_path, voice=voice, robotic=robotic)
        audio_bytes = tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)

    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")


async def _run_pipeline(job_id: str, req: GenerateRequest, base_url: str = "http://localhost:8000"):
    rid = req.request_id  # Supabase video_requests row ID (may be None)
    try:
        out_dir = job_dir(job_id)
        is_github_url = req.prompt.strip().startswith("https://github.com/")
        jtype = "repo" if is_github_url else "prompt"

        if rid:
            update_request_status(rid, "generating_script", backend_job_id=job_id, job_type=jtype)

        if is_github_url:
            await _run_repo_pipeline(job_id, req, out_dir, base_url)
        else:
            # Classify prompt: code vs concept/algo
            _set(job_id, status=JobStatus.running, progress="Classifying prompt…")
            prompt_type = await asyncio.to_thread(classify_prompt, req.prompt)
            logger.info("[%s] Prompt classified as: %s", job_id, prompt_type)

            if prompt_type == "concept_algo":
                if rid:
                    update_request_status(rid, "generating_script", job_type="concept_algo")
                await _run_concept_algo_pipeline(job_id, req, out_dir, base_url)
            else:
                await _run_prompt_pipeline(job_id, req, out_dir, base_url)

        if rid:
            video_url = _jobs[job_id].get("final_url") or _jobs[job_id].get("animation_url")
            update_request_status(rid, "completed", video_url=video_url)

    except HTTPException as exc:
        _set(job_id, status=JobStatus.failed, progress="Failed", error=exc.detail)
        if rid:
            update_request_status(rid, "failed", error=exc.detail)
        raise
    except Exception as exc:
        _set(job_id, status=JobStatus.failed, progress="Failed", error=str(exc))
        if rid:
            update_request_status(rid, "failed", error=str(exc))
        raise


# ── Repo pipeline (React Flow) ───────────────────────────────────────────────

async def _run_repo_pipeline(
    job_id: str, req: GenerateRequest, out_dir: Path, base_url: str,
):
    rid = req.request_id
    _set(job_id, status=JobStatus.running, job_type=JobType.repo, progress="Ingesting GitHub repo…")
    logger.info("[%s] Ingesting repo: %s", job_id, req.prompt.strip())

    try:
        repo_content = await ingest_github_repo(req.prompt.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Could not fetch repo (HTTP {exc.response.status_code}): {req.prompt}",
        )
    logger.info("[%s] Repo ingested — %d chars", job_id, len(repo_content))

    # Stage 1: Architecture
    _set(job_id, progress="Analyzing architecture…")
    if rid:
        update_request_status(rid, "generating_script")
    architecture = await asyncio.to_thread(
        analyze_repo, repo_content, req.mood, req.level,
    )
    arch_dict = architecture.model_dump(by_alias=True)
    (out_dir / "architecture.json").write_text(json.dumps(arch_dict, indent=2))
    _set(job_id, architecture=arch_dict)

    # Stage 2: Storyboard
    _set(job_id, progress="Generating storyboard…")
    if rid:
        update_request_status(rid, "rendering")
    storyboard = await asyncio.to_thread(generate_storyboard, architecture)
    sb_dict = storyboard.model_dump()
    (out_dir / "storyboard.json").write_text(json.dumps(sb_dict, indent=2))
    _set(job_id, storyboard=sb_dict)

    # Stage 3: Narration (assembly + LLM polish pass)
    _set(job_id, progress="Polishing narration…")
    narration = await asyncio.to_thread(assemble_narration, storyboard, architecture.summary)
    narr_dict = narration.model_dump()

    # ── Per-scene TTS audio ───────────────────────────────────────────────────
    if settings.runware_api_key:
        _set(job_id, progress="Generating scene audio…")
        if rid:
            update_request_status(rid, "adding_voiceover")
        scene_voice = req.voice or AVATAR_VOICES.get(req.avatar or "", "Oliver")
        logger.info("[%s] Generating per-scene TTS (%d scenes) voice=%s robotic=%s", job_id, len(narration.scenes), scene_voice, req.robotic)

        # Generate all scene audio files in parallel
        scene_tts_tasks = []
        for i, sn in enumerate(narration.scenes):
            if sn.narration.strip():
                out_path = out_dir / f"scene_{i}.mp3"
                scene_tts_tasks.append((i, generate_tts_audio(sn.narration, out_path, voice=scene_voice, robotic=req.robotic)))

        for i, task in scene_tts_tasks:
            try:
                await task
                narr_dict["scenes"][i]["audio_url"] = f"{base_url}/files/{job_id}/scene_{i}.mp3"
                logger.info("[%s] Scene %d TTS done", job_id, i)
            except Exception as exc:
                logger.warning("[%s] Scene %d TTS failed: %s", job_id, i, exc)

    (out_dir / "narration.json").write_text(json.dumps(narr_dict, indent=2))
    _set(job_id, narration=narr_dict)

    # Build TTS script for VEED avatars (intro/outro)
    tts_info = narration_to_tts_info(narration)
    tts_response = TTSScriptResponse(
        intro=narration.intro,
        info=tts_info,
        outro=narration.outro,
    )
    _set(job_id, tts_script=tts_response)

    logger.info(
        "[%s] ── TTS SCRIPT ───\n  INTRO: %s\n  INFO:  %s\n  OUTRO: %s\n───────",
        job_id, narration.intro, tts_info[:200], narration.outro,
    )

    # ── Avatar videos (intro + outro talking head) ────────────────────────────
    if settings.runware_api_key and settings.fal_key:
        _set(job_id, progress="Generating avatar videos…")
        if rid:
            update_request_status(rid, "finalizing")
        avatar_image_url = req.avatar_image_url or AVATAR_IMAGES.get(req.avatar or "", settings.avatar_image_url) or settings.avatar_image_url
        avatar_voice = req.voice or AVATAR_VOICES.get(req.avatar or "", "Oliver")
        try:
            veed = await run_veed_pipeline(
                intro_text=narration.intro,
                info_text=tts_info,
                outro_text=narration.outro,
                job_dir=out_dir,
                avatar_image_url=avatar_image_url,
                voice=avatar_voice,
                robotic=req.robotic,
            )
            # Inject video URLs into narration dict
            narr_dict["intro_video_url"] = f"{base_url}/files/{job_id}/intro.mp4"
            narr_dict["outro_video_url"] = f"{base_url}/files/{job_id}/outro.mp4"
            _set(job_id, narration=narr_dict)
        except Exception as exc:
            logger.warning("[%s] VEED avatar pipeline failed (non-fatal): %s", job_id, exc)

    _set(job_id, status=JobStatus.done, progress="Done")


# ── Prompt pipeline (structured explanation) ────────────────────────────────

async def _run_prompt_pipeline(
    job_id: str, req: GenerateRequest, out_dir: Path, base_url: str,
):
    rid = req.request_id
    _set(job_id, status=JobStatus.running, job_type=JobType.prompt, progress="Enriching prompt…")
    enriched_prompt = await enrich_prompt(req.prompt, req.url)

    # Stage 1: Structured explanation
    _set(job_id, progress="Analyzing concept…")
    if rid:
        update_request_status(rid, "generating_script")
    explanation = await asyncio.to_thread(
        analyze_prompt, enriched_prompt, req.mood, req.level,
    )
    expl_dict = explanation.model_dump(by_alias=True)
    (out_dir / "explanation.json").write_text(json.dumps(expl_dict, indent=2))
    _set(job_id, explanation=expl_dict)

    # Stage 2: Storyboard
    _set(job_id, progress="Generating storyboard…")
    if rid:
        update_request_status(rid, "rendering")
    storyboard = await asyncio.to_thread(generate_prompt_storyboard, explanation)
    sb_dict = storyboard.model_dump()
    (out_dir / "storyboard.json").write_text(json.dumps(sb_dict, indent=2))
    _set(job_id, storyboard=sb_dict)

    # Stage 3: Narration
    _set(job_id, progress="Polishing narration…")
    narration = await asyncio.to_thread(assemble_prompt_narration, storyboard, explanation.summary)
    narr_dict = narration.model_dump()

    # ── Per-scene TTS audio ───────────────────────────────────────────────────
    if settings.runware_api_key:
        _set(job_id, progress="Generating scene audio…")
        if rid:
            update_request_status(rid, "adding_voiceover")
        scene_voice = req.voice or AVATAR_VOICES.get(req.avatar or "", "Oliver")
        logger.info("[%s] Generating per-scene TTS (%d scenes) voice=%s robotic=%s", job_id, len(narration.scenes), scene_voice, req.robotic)

        scene_tts_tasks = []
        for i, sn in enumerate(narration.scenes):
            if sn.narration.strip():
                out_path = out_dir / f"scene_{i}.mp3"
                scene_tts_tasks.append((i, generate_tts_audio(sn.narration, out_path, voice=scene_voice, robotic=req.robotic)))

        for i, task in scene_tts_tasks:
            try:
                await task
                narr_dict["scenes"][i]["audio_url"] = f"{base_url}/files/{job_id}/scene_{i}.mp3"
                logger.info("[%s] Scene %d TTS done", job_id, i)
            except Exception as exc:
                logger.warning("[%s] Scene %d TTS failed: %s", job_id, i, exc)

    (out_dir / "narration.json").write_text(json.dumps(narr_dict, indent=2))
    _set(job_id, narration=narr_dict)

    # Build TTS script for VEED avatars (intro/outro)
    tts_info = prompt_narration_to_tts_info(narration)
    tts_response = TTSScriptResponse(
        intro=narration.intro,
        info=tts_info,
        outro=narration.outro,
    )
    _set(job_id, tts_script=tts_response)

    logger.info(
        "[%s] ── TTS SCRIPT ───\n  INTRO: %s\n  INFO:  %s\n  OUTRO: %s\n───────",
        job_id, narration.intro, tts_info[:200], narration.outro,
    )

    # ── Avatar videos (intro + outro talking head) ────────────────────────────
    if settings.runware_api_key and settings.fal_key:
        _set(job_id, progress="Generating avatar videos…")
        if rid:
            update_request_status(rid, "finalizing")
        avatar_image_url = req.avatar_image_url or AVATAR_IMAGES.get(req.avatar or "", settings.avatar_image_url) or settings.avatar_image_url
        avatar_voice = req.voice or AVATAR_VOICES.get(req.avatar or "", "Oliver")
        try:
            veed = await run_veed_pipeline(
                intro_text=narration.intro,
                info_text=tts_info,
                outro_text=narration.outro,
                job_dir=out_dir,
                avatar_image_url=avatar_image_url,
                voice=avatar_voice,
                robotic=req.robotic,
            )
            narr_dict["intro_video_url"] = f"{base_url}/files/{job_id}/intro.mp4"
            narr_dict["outro_video_url"] = f"{base_url}/files/{job_id}/outro.mp4"
            _set(job_id, narration=narr_dict)
        except Exception as exc:
            logger.warning("[%s] VEED avatar pipeline failed (non-fatal): %s", job_id, exc)

    _set(job_id, status=JobStatus.done, progress="Done")


# ── Concept/Algo pipeline (constrained single-scene Manim) ──────────────────

async def _run_concept_algo_pipeline(
    job_id: str, req: GenerateRequest, out_dir: Path, base_url: str,
):
    """Premium concept/algo path: single-scene Manim animation."""
    rid = req.request_id
    _set(job_id, status=JobStatus.running, job_type=JobType.concept_algo, progress="Enriching prompt…")

    enriched_prompt = await enrich_prompt(req.prompt, req.url)

    # Stage 1: Generate constrained single-scene Manim
    _set(job_id, progress="Generating concept animation…")
    if rid:
        update_request_status(rid, "generating_script")
    concept_result = await asyncio.to_thread(
        generate_concept_manim, enriched_prompt, req.mood, req.level,
    )

    # Save the manim script for debugging
    (out_dir / "concept_manim.py").write_text(concept_result.manim_script)

    # Stage 2: Render Manim
    _set(job_id, progress="Rendering animation…")
    if rid:
        update_request_status(rid, "rendering")
    try:
        animation_path = await render_manim(
            out_dir,
            script_str=concept_result.manim_script,
            scene_class="GeneratedScene",
            output_name="animation",
        )
        # Copy to a predictable location
        final_path = out_dir / "animation.mp4"
        if animation_path != final_path:
            shutil.copy2(animation_path, final_path)
        animation_url = f"{base_url}/files/{job_id}/animation.mp4"
        _set(job_id, animation_url=animation_url)
        logger.info("[%s] Manim render complete: %s", job_id, animation_path)
    except Exception as exc:
        logger.error("[%s] Manim render failed: %s", job_id, exc)
        raise

    # Build TTS script
    tts_response = TTSScriptResponse(
        intro=concept_result.intro,
        info=concept_result.info,
        outro=concept_result.outro,
    )
    _set(job_id, tts_script=tts_response)

    # ── TTS audio for the info narration ──────────────────────────────────────
    if settings.runware_api_key:
        _set(job_id, progress="Generating voiceover…")
        if rid:
            update_request_status(rid, "adding_voiceover")
        scene_voice = req.voice or AVATAR_VOICES.get(req.avatar or "", "Oliver")

        # Generate info narration audio
        if concept_result.info.strip():
            info_audio_path = out_dir / "info_narration.mp3"
            try:
                await generate_tts_audio(concept_result.info, info_audio_path, voice=scene_voice, robotic=req.robotic)
                logger.info("[%s] Info TTS done", job_id)
            except Exception as exc:
                logger.warning("[%s] Info TTS failed: %s", job_id, exc)

    # ── Avatar videos (intro + outro) + final merge ───────────────────────────
    if settings.runware_api_key and settings.fal_key:
        _set(job_id, progress="Generating avatar videos…")
        if rid:
            update_request_status(rid, "finalizing")
        avatar_image_url = req.avatar_image_url or AVATAR_IMAGES.get(req.avatar or "", settings.avatar_image_url) or settings.avatar_image_url
        avatar_voice = req.voice or AVATAR_VOICES.get(req.avatar or "", "Oliver")
        try:
            await run_veed_pipeline(
                intro_text=concept_result.intro,
                info_text=concept_result.info,
                outro_text=concept_result.outro,
                job_dir=out_dir,
                avatar_image_url=avatar_image_url,
                voice=avatar_voice,
                robotic=req.robotic,
            )
            # Merge intro + animation (with info audio) + outro → final.mp4
            intro_mp4 = out_dir / "intro.mp4"
            outro_mp4 = out_dir / "outro.mp4"
            animation_mp4 = out_dir / "animation.mp4"
            info_audio = out_dir / "info_narration.mp3"
            # Use info.mp3 as fallback (VEED also writes this)
            if not info_audio.exists():
                info_audio = out_dir / "info.mp3"
            if intro_mp4.exists() and outro_mp4.exists() and animation_mp4.exists() and info_audio.exists():
                _set(job_id, progress="Merging final video…")
                final_path = out_dir / "final.mp4"
                try:
                    await asyncio.to_thread(
                        merge_final, intro_mp4, animation_mp4, info_audio, outro_mp4, final_path,
                    )
                    _set(job_id, final_url=f"{base_url}/files/{job_id}/final.mp4")
                    logger.info("[%s] Final merge complete: %s", job_id, final_path)
                except Exception as merge_exc:
                    logger.warning("[%s] Final merge failed (non-fatal): %s", job_id, merge_exc)
            else:
                logger.warning("[%s] Missing files for final merge, skipping", job_id)
        except Exception as exc:
            logger.warning("[%s] VEED avatar pipeline failed (non-fatal): %s", job_id, exc)

    # Ensure final_url is always set (fallback to animation_url)
    if not _jobs[job_id].get("final_url"):
        _set(job_id, final_url=_jobs[job_id].get("animation_url"))

    _set(job_id, status=JobStatus.done, progress="Done")
