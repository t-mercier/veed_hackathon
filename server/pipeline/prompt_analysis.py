
"""
Stage 1: Structured explanation extraction via Mistral.

Given a user prompt (code snippet, concept, method) plus optional repo context,
produces a structured Explanation describing parts and relationships.

Also provides classify_prompt() to route between code vs concept/algo paths.
"""

import json
import logging

from .prompt_models import Explanation, Part, PartRelationship
from . import strip_json_fences

logger = logging.getLogger(__name__)

# ── Classification prompt ─────────────────────────────────────────────────────

_CLASSIFY_PROMPT = """\
You are classifying a user request about programming.

Decide whether the user is asking to explain:

A) **code** — a specific code snippet, function, method, class, or block of code.
   Examples: "explain this function", "what does this code do", "explain this try/catch block",
   "explain the fetchUser method", "walk me through this snippet"

B) **concept_algo** — a programming concept, algorithm, data structure, or abstract idea
   that benefits from visual/animated demonstration.
   Examples: "explain how malloc works", "explain binary search", "explain recursion",
   "how do pointers work", "explain memory allocation", "how does a linked list work",
   "explain how arrays work in memory"

User request:
{prompt}

Return ONLY one word: either "code" or "concept_algo"
"""


def classify_prompt(prompt: str) -> str:
    """Classify the user prompt as 'code' or 'concept_algo'.

    Returns 'code' or 'concept_algo'.
    """
    from .scripts import _chat

    logger.info("[prompt-classify] Classifying prompt type")
    raw = _chat(
        system="You are a classifier. Return only one word.",
        user=_CLASSIFY_PROMPT.format(prompt=prompt[:2000]),
        temperature=0.0,
    ).strip().lower()

    # Parse — be lenient
    if "concept" in raw or "algo" in raw:
        result = "concept_algo"
    else:
        result = "code"

    logger.info("[prompt-classify] Result: %s (raw: %s)", result, raw[:50])
    return result


# ── Explanation prompt ────────────────────────────────────────────────────────

_EXPLANATION_PROMPT = """\
You are a senior software educator analyzing a code snippet or programming concept.
Your goal is to produce a structured explanation suitable for an animated visual walkthrough.

Target audience: {level} developer. Tone: {mood}.

{repo_context_instruction}

{prompt_content}

Analyze this and identify 3–7 meaningful parts (blocks, phases, concepts, steps).
Think pedagogically — what are the key ideas a student needs to understand?

Return ONLY a valid JSON object (no markdown fences, no explanation):
{{
  "title": "Short descriptive title (max 60 chars)",
  "summary": "One sentence: what does this snippet/concept do?",
  "explanation_type": "code_snippet|concept|function|method",
  "parts": [
    {{
      "id": "snake_case_id",
      "label": "Human Label (max 20 chars)",
      "kind": "phase|concept|function|variable|step|block",
      "description": "One sentence describing what this part does or means"
    }}
  ],
  "relationships": [
    {{
      "id": "rel_1",
      "from": "part_id",
      "to": "part_id",
      "label": "Short edge label describing the connection"
    }}
  ]
}}

Rules:
- 3–7 parts (prefer 4–6)
- Part labels: max 20 chars
- Every relationship must reference valid part ids
- Focus on teaching — what matters for understanding, not exhaustive detail
- Return ONLY raw JSON
"""

_REPO_CONTEXT_NOTE = """\
IMPORTANT: The user has provided a GitHub repository as additional context.
The repository information below helps you understand the surrounding codebase, architecture,
and naming conventions. Use it to give a more informed and accurate explanation.
However, keep the explanation focused on the user's specific question/snippet — do NOT
switch into a full repository overview. The repo is context, not the main subject."""

_NO_REPO_CONTEXT_NOTE = ""


def _has_repo_context(enriched_prompt: str) -> bool:
    """Detect if the enriched prompt contains injected repo context."""
    return "--- Context from" in enriched_prompt and "=== Repository:" in enriched_prompt


def analyze_prompt(
    enriched_prompt: str,
    mood: str = "friendly",
    level: str = "beginner",
) -> Explanation:
    """Call Mistral to extract a structured Explanation from the user prompt."""
    from .scripts import _chat

    repo_instruction = _REPO_CONTEXT_NOTE if _has_repo_context(enriched_prompt) else _NO_REPO_CONTEXT_NOTE

    logger.info("[prompt-analysis] Generating explanation JSON (has_repo_context=%s)", bool(repo_instruction))
    raw = _chat(
        system="You are a software educator. Return only valid JSON, no markdown.",
        user=_EXPLANATION_PROMPT.format(
            prompt_content=enriched_prompt,
            mood=mood,
            level=level,
            repo_context_instruction=repo_instruction,
        ),
        temperature=0.3,
    )

    try:
        data = json.loads(strip_json_fences(raw))
    except json.JSONDecodeError as exc:
        logger.error("Explanation LLM returned invalid JSON: %s\n%s", exc, raw[:500])
        raise ValueError(f"Explanation extraction failed: {exc}") from exc

    parts = [
        Part(
            id=p.get("id", f"part_{i}"),
            label=p.get("label", p.get("id", f"Part {i}")),
            kind=p.get("kind", "phase"),
            description=p.get("description", ""),
        )
        for i, p in enumerate(data.get("parts", []))
    ]

    valid_ids = {p.id for p in parts}

    relationships = [
        PartRelationship(
            id=r.get("id", f"rel_{i}"),
            **{"from": r.get("from", ""), "to": r.get("to", "")},
            label=r.get("label", ""),
        )
        for i, r in enumerate(data.get("relationships", []))
        if r.get("from") in valid_ids and r.get("to") in valid_ids
    ]

    explanation = Explanation(
        title=data.get("title", "Explanation"),
        summary=data.get("summary", ""),
        explanation_type=data.get("explanation_type", "code_snippet"),
        parts=parts,
        relationships=relationships,
    )

    logger.info(
        "[prompt-analysis] Explanation: %d parts, %d relationships",
        len(explanation.parts), len(explanation.relationships),
    )
    return explanation
