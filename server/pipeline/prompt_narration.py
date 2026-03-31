"""
Stage 3: Narration assembly from PromptStoryboard.

Collects per-scene narration from the storyboard and produces:
- A PromptNarration object (scene-level granularity)
- A flattened info string for the VEED avatar pipeline

Includes an LLM polish pass to remove repetition and ensure smooth transitions.
"""

import json
import logging

from .prompt_models import PromptStoryboard, PromptNarration, SceneNarration
from . import strip_json_fences

logger = logging.getLogger(__name__)

_POLISH_PROMPT = """\
You are a script editor polishing a narrated walkthrough of a code concept.

Below is a JSON object containing:
- "intro": the opening narration (spoken by an avatar before the visual starts)
- "scenes": a list of scene narrations (each played during the visual)
- "outro": the closing narration (spoken by the avatar after the visual ends)

Your job:
1. Remove any repetition — if a sentence or idea appears in the intro AND in a scene,
   keep it only where it fits best. Same for outro vs last scene.
2. Ensure smooth transitions between consecutive scenes.
3. The intro should be a brief, engaging hook (1–2 sentences).
4. The outro should be a concise wrap-up (1–2 sentences).
5. Keep the tone conversational and educational.
6. Do NOT change technical terms or the overall structure.
7. Keep each scene narration to 2–3 sentences max.

Input:
{narration_json}

Return ONLY valid JSON with the same structure (intro, scenes array with scene_id + narration, outro).
No markdown fences.
"""


def _polish_narration(narration: PromptNarration) -> PromptNarration:
    """LLM pass to deduplicate and smooth the full narration script."""
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

        polished_by_id = {
            s.get("scene_id", ""): s.get("narration", "")
            for s in data.get("scenes", [])
        }

        merged_scenes = []
        for orig in narration.scenes:
            text = polished_by_id.get(orig.scene_id, orig.narration)
            merged_scenes.append(SceneNarration(scene_id=orig.scene_id, narration=text or orig.narration))

        polished = PromptNarration(
            intro=data.get("intro", narration.intro),
            scenes=merged_scenes,
            outro=data.get("outro", narration.outro),
        )
        logger.info(
            "[prompt-narration] Polish pass succeeded — %d scenes",
            len(polished.scenes),
        )
        return polished

    except Exception as exc:
        logger.warning("[prompt-narration] Polish pass failed, using raw narration: %s", exc)
        return narration


def assemble_prompt_narration(storyboard: PromptStoryboard, summary: str = "") -> PromptNarration:
    """
    Build narration from storyboard scenes, then polish via LLM.
    """
    if not storyboard.scenes:
        return PromptNarration(
            intro=summary or "Let's explore this concept.",
            scenes=[],
            outro="That's the overview. Thanks for watching!",
        )

    first = storyboard.scenes[0]

    intro = summary or first.narration or "Let's break this down step by step."

    scene_narrations = [
        SceneNarration(scene_id=s.id, narration=s.narration)
        for s in storyboard.scenes
    ]

    outro = f"That covers {summary.split('.')[0].lower() if summary else 'this concept'}. Thanks for watching!"

    raw_narration = PromptNarration(
        intro=intro,
        scenes=scene_narrations,
        outro=outro,
    )

    logger.info("[prompt-narration] Raw narration: %d scenes — running polish pass", len(scene_narrations))
    polished = _polish_narration(raw_narration)
    return polished


def narration_to_tts_info(narration: PromptNarration) -> str:
    """Flatten scene narrations into a single 'info' string for the VEED TTS pipeline."""
    middle_scenes = narration.scenes[1:-1] if len(narration.scenes) > 2 else narration.scenes
    return " ".join(s.narration for s in middle_scenes if s.narration)
