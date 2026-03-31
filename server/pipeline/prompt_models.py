"""
Pydantic models for the prompt-explainer pipeline.

Three stages: Explanation → Storyboard → Narration.
All structures are JSON-serializable for the frontend scene renderer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Stage 1: Explanation ──────────────────────────────────────────────────────

class Part(BaseModel):
    id: str
    label: str
    kind: str = "phase"  # phase, concept, function, variable, step, block
    description: str = ""

class PartRelationship(BaseModel):
    id: str
    source: str = Field(alias="from", serialization_alias="from")
    target: str = Field(alias="to", serialization_alias="to")
    label: str = ""

    class Config:
        populate_by_name = True

class Explanation(BaseModel):
    title: str
    summary: str = ""
    explanation_type: str = "code_snippet"  # code_snippet, concept, function, method
    parts: list[Part] = Field(default_factory=list)
    relationships: list[PartRelationship] = Field(default_factory=list)


# ── Stage 2: Storyboard ──────────────────────────────────────────────────────

class ScenePanel(BaseModel):
    title: str = ""
    bullets: list[str] = Field(default_factory=list)

class PromptScene(BaseModel):
    id: str
    title: str
    goal: str = ""
    visible_parts: list[str] = Field(default_factory=list)
    highlighted_parts: list[str] = Field(default_factory=list)
    highlighted_relationships: list[str] = Field(default_factory=list)
    camera_mode: str = "fit"  # fit, focus
    focus_part: str | None = None
    narration: str = ""
    panel: ScenePanel | None = None

class PromptStoryboard(BaseModel):
    scenes: list[PromptScene] = Field(default_factory=list)


# ── Stage 3: Narration ───────────────────────────────────────────────────────

class SceneNarration(BaseModel):
    scene_id: str
    narration: str

class PromptNarration(BaseModel):
    intro: str = ""
    scenes: list[SceneNarration] = Field(default_factory=list)
    outro: str = ""
