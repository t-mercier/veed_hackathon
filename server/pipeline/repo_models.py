"""
Pydantic models for the repo-explainer pipeline.

Three stages: Architecture → Storyboard → Narration.
All structures are JSON-serializable for the React Flow frontend.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Stage 1: Architecture ─────────────────────────────────────────────────────

class Component(BaseModel):
    id: str
    label: str
    type: str = "module"  # frontend, backend, database, service, library, module, config, cli
    paths: list[str] = Field(default_factory=list)
    responsibility: str = ""

class Relationship(BaseModel):
    id: str
    source: str = Field(alias="from", serialization_alias="from")
    target: str = Field(alias="to", serialization_alias="to")
    kind: str = "calls"  # calls, http, imports, emits, reads, writes
    label: str = ""

    class Config:
        populate_by_name = True

class Flow(BaseModel):
    id: str
    title: str
    steps: list[str]  # component ids in execution order

class Architecture(BaseModel):
    repo_name: str
    summary: str = ""
    entrypoints: list[str] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    flows: list[Flow] = Field(default_factory=list)


# ── Stage 2: Storyboard ──────────────────────────────────────────────────────

class ScenePanel(BaseModel):
    title: str = ""
    bullets: list[str] = Field(default_factory=list)

class Scene(BaseModel):
    id: str
    title: str
    goal: str = ""
    visible_components: list[str] = Field(default_factory=list)
    highlighted_components: list[str] = Field(default_factory=list)
    highlighted_relationships: list[str] = Field(default_factory=list)
    camera_mode: str = "fit"  # fit, focus
    focus_component: str | None = None
    narration: str = ""
    panel: ScenePanel | None = None

class Storyboard(BaseModel):
    scenes: list[Scene] = Field(default_factory=list)


# ── Stage 3: Narration ───────────────────────────────────────────────────────

class SceneNarration(BaseModel):
    scene_id: str
    narration: str

class RepoNarration(BaseModel):
    intro: str = ""
    scenes: list[SceneNarration] = Field(default_factory=list)
    outro: str = ""
