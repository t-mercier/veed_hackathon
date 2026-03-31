"""
Stage 2: Storyboard generation from Architecture.

Takes a structured Architecture and produces an ordered sequence of Scenes
that form a teaching progression: overview → flow → component focuses → recap.
"""

import json
import logging

from .repo_models import Architecture, Storyboard, Scene, ScenePanel
from . import strip_json_fences

logger = logging.getLogger(__name__)

_STORYBOARD_PROMPT = """\
You are an educational content designer creating an animated architecture walkthrough.

Given the following repository architecture, produce a storyboard: an ordered sequence
of 5–7 scenes that explain the system progressively, like a guided tree traversal.

Architecture:
{architecture_json}

Scene progression MUST follow this exact pattern:
1. Global overview — all components visible and highlighted — camera_mode "fit"
2–5. Component deep dives — traverse in tree order: start from leaf components
     (those with no outgoing calls or dependencies), then work up through branches
     toward root/entry components. Each scene focuses on ONE component.
     - ALL components must remain visible (they form the background graph)
     - highlighted_components: [the focused component] only
     - highlighted_relationships: only relationships involving the focused component
     - camera_mode "focus" with focus_component set
6. Recap — all components visible and all highlighted — camera_mode "fit"

CRITICAL RULES:
- visible_components MUST always contain ALL component IDs (every scene, no exceptions)
  Other nodes appear dimmed in the background — this is how the user sees the full graph
  while focusing on one node at a time
- camera_mode is "focus" for deep dives, "fit" for overview and recap
- Narration: plain spoken English, no markdown, 2–3 sentences per scene
- Each scene narration must be unique — do NOT repeat sentences or ideas across scenes
- All component/relationship IDs must exactly match the architecture JSON
- Return ONLY raw JSON (no markdown fences)

Return format:
{{
  "scenes": [
    {{
      "id": "scene_1",
      "title": "Scene Title",
      "goal": "What this scene teaches",
      "visible_components": ["ALL", "component", "ids", "here"],
      "highlighted_components": ["focused_comp_id"],
      "highlighted_relationships": ["rel_id_1"],
      "camera_mode": "fit",
      "focus_component": null,
      "narration": "Plain spoken English narration for this scene.",
      "panel": {{
        "title": "Panel Title",
        "bullets": ["Key point 1", "Key point 2"]
      }}
    }}
  ]
}}
"""


def generate_storyboard(architecture: Architecture) -> Storyboard:
    """Call Mistral to generate a teaching storyboard from the architecture."""
    from .scripts import _chat

    arch_json = architecture.model_dump(by_alias=True)

    logger.info("[repo-storyboard] Generating storyboard")
    raw = _chat(
        system="You are an educational designer. Return only valid JSON, no markdown.",
        user=_STORYBOARD_PROMPT.format(
            architecture_json=json.dumps(arch_json, indent=2),
        ),
        temperature=0.3,
    )

    try:
        data = json.loads(strip_json_fences(raw))
    except json.JSONDecodeError as exc:
        logger.warning("Storyboard LLM returned invalid JSON, using fallback: %s", exc)
        return _fallback_storyboard(architecture)

    scenes_data = data.get("scenes", [])
    if not scenes_data:
        return _fallback_storyboard(architecture)

    valid_comp_ids = {c.id for c in architecture.components}
    valid_rel_ids = {r.id for r in architecture.relationships}

    scenes = []
    for i, s in enumerate(scenes_data):
        scene = Scene(
            id=s.get("id", f"scene_{i}"),
            title=s.get("title", f"Scene {i + 1}"),
            goal=s.get("goal", ""),
            visible_components=[c for c in s.get("visible_components", []) if c in valid_comp_ids],
            highlighted_components=[c for c in s.get("highlighted_components", []) if c in valid_comp_ids],
            highlighted_relationships=[r for r in s.get("highlighted_relationships", []) if r in valid_rel_ids],
            camera_mode=s.get("camera_mode", "fit"),
            focus_component=s.get("focus_component") if s.get("focus_component") in valid_comp_ids else None,
            narration=s.get("narration", ""),
            panel=ScenePanel(**s["panel"]) if s.get("panel") else None,
        )
        # Always show all components — highlighting + dimming handles visual focus
        scene.visible_components = list(valid_comp_ids)
        scenes.append(scene)

    storyboard = Storyboard(scenes=scenes)
    logger.info("[repo-storyboard] Generated %d scenes", len(storyboard.scenes))
    return storyboard


def _fallback_storyboard(arch: Architecture) -> Storyboard:
    """Deterministic fallback if LLM storyboard fails."""
    all_ids = [c.id for c in arch.components]
    all_rel_ids = [r.id for r in arch.relationships]

    scenes = [
        Scene(
            id="overview",
            title="Project Overview",
            goal="Introduce all components at a high level",
            visible_components=all_ids,
            highlighted_components=all_ids[:3],
            highlighted_relationships=all_rel_ids[:3],
            camera_mode="fit",
            narration=f"{arch.repo_name} is composed of {len(arch.components)} main components. {arch.summary}",
            panel=ScenePanel(
                title="Architecture",
                bullets=[c.responsibility or c.label for c in arch.components[:4]],
            ),
        ),
    ]

    # Add a focus scene for each component (up to 4)
    for c in arch.components[:4]:
        related_rels = [
            r.id for r in arch.relationships
            if r.source == c.id or r.target == c.id
        ]
        connected = set()
        for r in arch.relationships:
            if r.source == c.id:
                connected.add(r.target)
            elif r.target == c.id:
                connected.add(r.source)

        scenes.append(Scene(
            id=f"focus_{c.id}",
            title=c.label,
            goal=f"Understand the {c.label} component",
            visible_components=all_ids,   # all visible, others dimmed
            highlighted_components=[c.id],
            highlighted_relationships=related_rels[:3],
            camera_mode="focus",
            focus_component=c.id,
            narration=c.responsibility or f"The {c.label} component handles a key part of the system.",
            panel=ScenePanel(
                title=c.label,
                bullets=[f"Type: {c.type}"] + ([f"Files: {', '.join(c.paths[:3])}"] if c.paths else []),
            ),
        ))

    scenes.append(Scene(
        id="recap",
        title="Recap",
        goal="Summarize the full architecture",
        visible_components=all_ids,
        highlighted_components=all_ids,
        highlighted_relationships=all_rel_ids,
        camera_mode="fit",
        narration=f"That's the full picture of {arch.repo_name}. {arch.summary}",
        panel=ScenePanel(
            title="Key Takeaways",
            bullets=[
                f"{len(arch.components)} components",
                f"{len(arch.relationships)} connections",
                arch.flows[0].title if arch.flows else "End-to-end flow",
            ],
        ),
    ))

    return Storyboard(scenes=scenes)
