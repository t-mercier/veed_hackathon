"""
Stage 1: Repo architecture extraction via Mistral.

Given repo content (from enrich.py), produces a structured Architecture object
describing components, relationships, and execution flows.
"""

import json
import logging

from .repo_models import Architecture, Component, Relationship, Flow
from . import strip_json_fences

logger = logging.getLogger(__name__)

_ARCHITECTURE_PROMPT = """\
You are a senior software architect analyzing a GitHub repository.
Your goal is to produce a structured architecture description suitable for
an educational animated explanation.

Target audience: {level} developer. Tone: {mood}.

{repo_content}

Analyze this repository and identify 5–9 meaningful architectural components.
Group related files into components. Do NOT just list folders — think in terms
of responsibilities, layers, and services.

Return ONLY a valid JSON object (no markdown fences, no explanation):
{{
  "repo_name": "short-repo-name",
  "summary": "One sentence: what does this project do?",
  "entrypoints": ["path/to/main.py"],
  "components": [
    {{
      "id": "snake_case_id",
      "label": "Human Label",
      "type": "backend|frontend|database|service|library|config|cli",
      "paths": ["src/auth/"],
      "responsibility": "One sentence describing what this component does"
    }}
  ],
  "relationships": [
    {{
      "id": "rel_1",
      "from": "component_id",
      "to": "component_id",
      "kind": "calls|http|imports|emits|reads|writes",
      "label": "Short edge label"
    }}
  ],
  "flows": [
    {{
      "id": "main_flow",
      "title": "Main execution flow",
      "steps": ["component_a", "component_b", "component_c"]
    }}
  ]
}}

Rules:
- 5–9 components (prefer 6–7)
- Component labels: max 20 chars
- Every relationship must reference valid component ids
- At least one flow showing the main execution path
- Prefer conceptual grouping over raw directory listing
- Return ONLY raw JSON
"""


def analyze_repo(
    repo_content: str,
    mood: str = "friendly",
    level: str = "beginner",
) -> Architecture:
    """Call Mistral to extract Architecture from repo content."""
    from .scripts import _chat

    logger.info("[repo-analysis] Generating architecture JSON")
    raw = _chat(
        system="You are a software architect. Return only valid JSON, no markdown.",
        user=_ARCHITECTURE_PROMPT.format(
            repo_content=repo_content,
            mood=mood,
            level=level,
        ),
        temperature=0.3,
    )

    try:
        data = json.loads(strip_json_fences(raw))
    except json.JSONDecodeError as exc:
        logger.error("Architecture LLM returned invalid JSON: %s\n%s", exc, raw[:500])
        raise ValueError(f"Architecture extraction failed: {exc}") from exc

    # Build with fallbacks for missing fields
    components = [
        Component(
            id=c.get("id", f"comp_{i}"),
            label=c.get("label", c.get("id", f"Component {i}")),
            type=c.get("type", "module"),
            paths=c.get("paths", []),
            responsibility=c.get("responsibility", ""),
        )
        for i, c in enumerate(data.get("components", []))
    ]

    valid_ids = {c.id for c in components}

    relationships = [
        Relationship(
            id=r.get("id", f"rel_{i}"),
            **{"from": r.get("from", ""), "to": r.get("to", "")},
            kind=r.get("kind", "calls"),
            label=r.get("label", ""),
        )
        for i, r in enumerate(data.get("relationships", []))
        if r.get("from") in valid_ids and r.get("to") in valid_ids
    ]

    flows = [
        Flow(
            id=f.get("id", f"flow_{i}"),
            title=f.get("title", "Main flow"),
            steps=[s for s in f.get("steps", []) if s in valid_ids],
        )
        for i, f in enumerate(data.get("flows", []))
    ]

    arch = Architecture(
        repo_name=data.get("repo_name", "repo"),
        summary=data.get("summary", ""),
        entrypoints=data.get("entrypoints", []),
        components=components,
        relationships=relationships,
        flows=flows,
    )

    logger.info(
        "[repo-analysis] Architecture: %d components, %d relationships, %d flows",
        len(arch.components), len(arch.relationships), len(arch.flows),
    )
    return arch
