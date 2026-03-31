"""
Stage 3: Narration assembly from Storyboard.

Collects per-scene narration from the storyboard and produces:
- A RepoNarration object (scene-level granularity)
- A TTSScript (intro/info/outro for the VEED avatar pipeline)

Includes an LLM polish pass to remove repetition and ensure smooth transitions.
"""

import json
import logging

from .repo_models import Storyboard, RepoNarration, SceneNarration
from . import strip_json_fences

logger = logging.getLogger(__name__)

# ── Polish prompt ─────────────────────────────────────────────────────────────

_POLISH_PROMPT = """\
You are a script editor polishing a narrated walkthrough of a software project.

Below is a JSON object containing:
- "intro": the opening narration (spoken by an avatar before the visual starts)
- "scenes": a list of scene narrations (each played during the visual)
- "outro": the closing narration (spoken by the avatar after the visual ends)

Your job:
1. Remove any repetition — if a sentence or idea appears in the intro AND in a scene,
   keep it only where it fits best. Same for outro vs last scene.
2. Ensure smooth transitions between consecutive scenes. Each scene should flow
   naturally from the previous one without re-introducing concepts already covered.
3. The intro should be a brief, engaging hook (1–2 sentences). Do NOT repeat the
   first scene's content in the intro.
4. The outro should be a concise wrap-up (1–2 sentences). Do NOT repeat the last
   scene's content in the outro.
5. Keep the tone conversational and educational.
6. Do NOT change component names, technical terms, or the overall structure.
7. Keep each scene narration to 2–3 sentences max.

Input:
{narration_json}

Return ONLY valid JSON with the same structure (intro, scenes array with scene_id + narration, outro).
No markdown fences.
"""


def _polish_narration(narration: RepoNarration) -> RepoNarration:
    """LLM pass to deduplicate and smooth the full narration script.

    IMPORTANT: The returned narration always has exactly the same number of
    scenes (and the same scene_ids in the same order) as the input.  If the
    LLM drops or reorders scenes we fall back to the originals so that the
    client can safely index narration and storyboard scenes by position.
    """
    from .scripts import _chat

    narr_input = {
        "intro": narration.intro,
        "scenes": [{"scene_id": s.scene_id, "narration": s.narration} for s in narration.scenes],
        "outro": narration.outro,
    }

    try:
        raw = _chat(
            system="You are a concise script editor. Return only valid JSON.",
            user=_POLISH_PROMPT.format(narration_json=json.dumps(narr_input, indent=2)),
            temperature=0.3,
        )
        data = json.loads(strip_json_fences(raw))

        # Build a lookup of polished narrations keyed by scene_id
        polished_by_id = {
            s.get("scene_id", ""): s.get("narration", "")
            for s in data.get("scenes", [])
        }

        # Rebuild scenes list preserving the original order and count.
        # Use polished text when available, fall back to original.
        merged_scenes = []
        for orig in narration.scenes:
            text = polished_by_id.get(orig.scene_id, orig.narration)
            merged_scenes.append(SceneNarration(scene_id=orig.scene_id, narration=text or orig.narration))

        polished = RepoNarration(
            intro=data.get("intro", narration.intro),
            scenes=merged_scenes,
            outro=data.get("outro", narration.outro),
        )
        logger.info(
            "[repo-narration] Polish pass succeeded — %d scenes (LLM returned %d, merged back to %d)",
            len(polished.scenes), len(polished_by_id), len(merged_scenes),
        )
        return polished

    except Exception as exc:
        logger.warning("[repo-narration] Polish pass failed, using raw narration: %s", exc)
        return narration


def assemble_narration(storyboard: Storyboard, repo_summary: str = "") -> RepoNarration:
    """
    Build narration from storyboard scenes, then polish via LLM to remove
    repetition and ensure smooth transitions.
    """
    if not storyboard.scenes:
        return RepoNarration(
            intro=repo_summary or "Let's explore this repository.",
            scenes=[],
            outro="That's the overview of the project.",
        )

    first = storyboard.scenes[0]
    last = storyboard.scenes[-1]

    # Intro: short hook derived from summary (NOT first scene narration)
    intro = repo_summary or first.narration or "Let's explore this project."

    # Per-scene narrations (all scenes, including first and last)
    scene_narrations = [
        SceneNarration(scene_id=s.id, narration=s.narration)
        for s in storyboard.scenes
    ]

    # Outro: wrap-up (NOT last scene narration verbatim)
    outro = f"That's the architecture of {repo_summary.split('.')[0].lower() if repo_summary else 'this project'}. Thanks for watching!"

    raw_narration = RepoNarration(
        intro=intro,
        scenes=scene_narrations,
        outro=outro,
    )

    logger.info("[repo-narration] Raw narration: %d scenes — running polish pass", len(scene_narrations))
    polished = _polish_narration(raw_narration)
    return polished


def narration_to_tts_info(narration: RepoNarration) -> str:
    """
    Flatten scene narrations into a single 'info' string for the VEED TTS pipeline.
    Skips the first and last scenes (those become intro/outro).
    """
    middle_scenes = narration.scenes[1:-1] if len(narration.scenes) > 2 else narration.scenes
    return " ".join(s.narration for s in middle_scenes if s.narration)
