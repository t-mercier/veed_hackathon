"""
Stage 2: Storyboard generation from Explanation.

Takes a structured Explanation and produces an ordered sequence of Scenes
that form a teaching progression: overview → part focuses → flow → recap.
"""

import json
import logging

from .prompt_models import Explanation, PromptStoryboard, PromptScene, ScenePanel
from . import strip_json_fences

logger = logging.getLogger(__name__)

_STORYBOARD_PROMPT = """\
You are an educational content designer creating an animated concept walkthrough.

Given the following structured explanation, produce a storyboard: an ordered sequence
of 4–6 scenes that explain the concept progressively, like a guided visual lesson.

Explanation:
{explanation_json}

Scene progression MUST follow this pattern:
1. Overview — all parts visible and highlighted — camera_mode "fit"
   Introduce the topic at a high level.
2–4. Part deep dives — each scene focuses on ONE part or a small group.
   - ALL parts must remain visible (they form the background graph)
   - highlighted_parts: [the focused part(s)] only
   - highlighted_relationships: only relationships involving the focused part(s)
   - camera_mode "focus" with focus_part set
5. Flow/Recap — all parts visible and all highlighted — camera_mode "fit"
   Show how everything connects and summarize the key takeaway.

CRITICAL RULES:
- visible_parts MUST always contain ALL part IDs (every scene, no exceptions)
  Other parts appear dimmed in the background
- camera_mode is "focus" for deep dives, "fit" for overview and recap
- Narration: plain spoken English, no markdown, 2–3 sentences per scene
- Each scene narration must be unique — do NOT repeat sentences across scenes
- All part/relationship IDs must exactly match the explanation JSON
- Return ONLY raw JSON (no markdown fences)

Return format:
{{
  "scenes": [
    {{
      "id": "scene_1",
      "title": "Scene Title",
      "goal": "What this scene teaches",
      "visible_parts": ["ALL", "part", "ids", "here"],
      "highlighted_parts": ["focused_part_id"],
      "highlighted_relationships": ["rel_id_1"],
      "camera_mode": "fit",
      "focus_part": null,
      "narration": "Plain spoken English narration for this scene.",
      "panel": {{
        "title": "Panel Title",
        "bullets": ["Key point 1", "Key point 2"]
      }}
    }}
  ]
}}
"""


def generate_prompt_storyboard(explanation: Explanation) -> PromptStoryboard:
    """Call Mistral to generate a teaching storyboard from the explanation."""
    from .scripts import _chat

    expl_json = explanation.model_dump(by_alias=True)

    logger.info("[prompt-storyboard] Generating storyboard")
    raw = _chat(
        system="You are an educational designer. Return only valid JSON, no markdown.",
        user=_STORYBOARD_PROMPT.format(
            explanation_json=json.dumps(expl_json, indent=2),
        ),
        temperature=0.3,
    )

    try:
        data = json.loads(strip_json_fences(raw))
    except json.JSONDecodeError as exc:
        logger.warning("Storyboard LLM returned invalid JSON, using fallback: %s", exc)
        return _fallback_storyboard(explanation)

    scenes_data = data.get("scenes", [])
    if not scenes_data:
        return _fallback_storyboard(explanation)

    valid_part_ids = {p.id for p in explanation.parts}
    valid_rel_ids = {r.id for r in explanation.relationships}

    scenes = []
    for i, s in enumerate(scenes_data):
        scene = PromptScene(
            id=s.get("id", f"scene_{i}"),
            title=s.get("title", f"Scene {i + 1}"),
            goal=s.get("goal", ""),
            visible_parts=[p for p in s.get("visible_parts", []) if p in valid_part_ids],
            highlighted_parts=[p for p in s.get("highlighted_parts", []) if p in valid_part_ids],
            highlighted_relationships=[r for r in s.get("highlighted_relationships", []) if r in valid_rel_ids],
            camera_mode=s.get("camera_mode", "fit"),
            focus_part=s.get("focus_part") if s.get("focus_part") in valid_part_ids else None,
            narration=s.get("narration", ""),
            panel=ScenePanel(**s["panel"]) if s.get("panel") else None,
        )
        # Always show all parts — highlighting + dimming handles visual focus
        scene.visible_parts = list(valid_part_ids)
        scenes.append(scene)

    storyboard = PromptStoryboard(scenes=scenes)
    logger.info("[prompt-storyboard] Generated %d scenes", len(storyboard.scenes))
    return storyboard


def _fallback_storyboard(expl: Explanation) -> PromptStoryboard:
    """Deterministic fallback if LLM storyboard fails."""
    all_ids = [p.id for p in expl.parts]
    all_rel_ids = [r.id for r in expl.relationships]

    scenes = [
        PromptScene(
            id="overview",
            title="Big Picture",
            goal="Introduce the topic at a high level",
            visible_parts=all_ids,
            highlighted_parts=all_ids,
            highlighted_relationships=all_rel_ids,
            camera_mode="fit",
            narration=f"{expl.title}. {expl.summary}",
            panel=ScenePanel(
                title="Overview",
                bullets=[p.description or p.label for p in expl.parts[:4]],
            ),
        ),
    ]

    # Add a focus scene for each part (up to 4)
    for p in expl.parts[:4]:
        related_rels = [
            r.id for r in expl.relationships
            if r.source == p.id or r.target == p.id
        ]
        scenes.append(PromptScene(
            id=f"focus_{p.id}",
            title=p.label,
            goal=f"Understand the {p.label} part",
            visible_parts=all_ids,
            highlighted_parts=[p.id],
            highlighted_relationships=related_rels[:3],
            camera_mode="focus",
            focus_part=p.id,
            narration=p.description or f"The {p.label} handles a key part of this concept.",
            panel=ScenePanel(
                title=p.label,
                bullets=[f"Type: {p.kind}", p.description] if p.description else [f"Type: {p.kind}"],
            ),
        ))

    scenes.append(PromptScene(
        id="recap",
        title="Key Takeaway",
        goal="Summarize the full explanation",
        visible_parts=all_ids,
        highlighted_parts=all_ids,
        highlighted_relationships=all_rel_ids,
        camera_mode="fit",
        narration=f"That's how {expl.title.lower()} works. {expl.summary}",
        panel=ScenePanel(
            title="Summary",
            bullets=[
                f"{len(expl.parts)} key parts",
                f"{len(expl.relationships)} connections",
                expl.summary or "End-to-end understanding",
            ],
        ),
    ))

    return PromptStoryboard(scenes=scenes)
