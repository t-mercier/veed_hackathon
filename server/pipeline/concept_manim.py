"""
Constrained single-scene Manim generation for concept/algorithm explanations.

Generates exactly ONE Manim scene plus intro/outro narration.
Used only for concept/algo Prompt Mode — not for code snippets.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ConceptManimResult:
    """Single-scene Manim output with narration."""
    manim_script: str
    intro: str
    info: str
    outro: str


_SYSTEM_PROMPT = """\
You are an expert Manim animator and computer science educator.

You will create a SINGLE Manim animation scene that visually explains a programming concept,
algorithm, or data structure.

CRITICAL CONSTRAINT: You must generate exactly ONE scene class named `GeneratedScene`.
All animation must happen within this single scene's construct() method.
Do NOT create multiple scenes or multiple classes.

MANIM RULES (follow EXACTLY — any violation will crash the render):
- The Scene class MUST be named exactly `GeneratedScene`
- Import only: `from manim import *`
- Do NOT use MathTex, Tex, or any LaTeX — use Text() for ALL text
- Do NOT use the Code() class — display code using Text() with font="Courier New"
- Do NOT use external images or custom fonts other than "Courier New"
- Do NOT use BulletedList() — use VGroup of Text() objects instead
- Do NOT use Brace or BraceBetweenPoints — they have known bugs and will crash
- Do NOT pass font_size as a keyword argument to any method except Text() constructor
  WRONG: brace.get_text("label", font_size=24)
  RIGHT: label = Text("label", font_size=24); label.next_to(brace, DOWN)
- Do NOT pass unexpected keyword arguments to .next_to(), .move_to(), .shift()
  These methods accept: (target, direction, buff, aligned_edge) — NOTHING else
- Target 20–40 seconds total runtime
- Use clear colours: WHITE, YELLOW, BLUE, GREEN, RED on dark background
- Show one concept at a time with labels and annotations
- ALWAYS call self.wait(1) between major steps
- Keep animations simple: Write, FadeIn, FadeOut, Create, GrowArrow, Transform
- SurroundingRectangle ONLY accepts a single Mobject or VGroup — NEVER pass a Python list
  WRONG: SurroundingRectangle(items[0:3], ...)
  RIGHT: SurroundingRectangle(VGroup(*items[0:3]), ...)
- VGroup slicing returns a list — always wrap with VGroup(*...) before passing to any Manim function

SAFE MANIM OBJECTS (use only these):
- Text, VGroup, Arrow, Rectangle, Circle, Square, Line, Dot
- Axes (for graphs), NumberLine
- SurroundingRectangle (single Mobject/VGroup only), Underline

FORBIDDEN OBJECTS (will crash — do NOT use):
- Brace, BraceBetweenPoints, ArcBrace
- Tex, MathTex, BulletedList, Code
- DecimalNumber, Integer, Variable

TITLE RULE (critical — always follow this pattern):
- If you show a title at the start, ALWAYS fade it out before the main animation begins
  CORRECT PATTERN:
    title = Text("Arrays", font_size=36, color=YELLOW).to_edge(UP)
    self.play(Write(title))
    self.wait(1)
    self.play(FadeOut(title))   # ← MANDATORY before showing main content
    # now show main animation below...
- NEVER keep a title visible while other content is animating — it will overlap

LAYOUT RULES (critical for visual quality — READ CAREFULLY):
- ALWAYS group related objects into a VGroup immediately after creating them
- ALWAYS call group.move_to(ORIGIN) or group.move_to(UP * 0.5) to center on screen
- For arrays/sequences: create all cells as a VGroup FIRST, then center the whole group
  CORRECT PATTERN:
    cells = VGroup()
    for i, val in enumerate([10, 20, 30, 40, 50]):
        box = Rectangle(width=1.0, height=1.0, color=BLUE)
        label = Text(str(val), font_size=28).move_to(box.get_center())
        cells.add(VGroup(box, label))
    cells.arrange(RIGHT, buff=0.1)
    cells.move_to(ORIGIN)   # ← MANDATORY: center the whole group
    self.play(Create(cells))
- For trees/graphs: build all nodes first as VGroup, then center
- NEVER position elements piecemeal with many .shift() calls — group first, center once
- Keep ALL content within ±5.5 units horizontally, ±3.5 units vertically
- Use font_size between 22-30 for readability
- Leave margins — don't pack elements edge-to-edge
- Clean up previous elements with FadeOut before showing new ones if screen gets crowded

NARRATION RULES:
- Plain spoken English, no markdown, no special characters
- INTRO: ~20 words, conversational greeting + topic introduction
- INFO: ~80–120 words — voiceover played DURING the animation.
  Explain the CONCEPT clearly, as a teacher would to a student.
  Structure it to match the logical flow of the animation (early steps first, later steps last),
  but DO NOT narrate the visuals themselves — never say things like
  "you can see the title", "the box appears", "fading in", "on screen now", etc.
  Just explain the concept as if you're talking someone through it.
  Example for recursion: "Recursion is when a function calls itself to solve a smaller version
  of the same problem. Each call adds a new frame to the call stack, until we hit the base case..."
- OUTRO: ~20 words, clear takeaway or summary

Return ONLY this exact format:

<manim_script>
[complete Python code for ONE scene]
</manim_script>

<intro>
[avatar intro speech]
</intro>

<info>
[animation voiceover for the single scene]
</info>

<outro>
[avatar outro speech]
</outro>"""


# ── Post-processing sanitizer ─────────────────────────────────────────────────

# Patterns that the LLM commonly generates despite instructions.
# Each tuple: (regex_pattern, replacement, description)
_SANITIZE_RULES: List[Tuple[re.Pattern, str, str]] = [
    # Remove Brace / BraceBetweenPoints / ArcBrace usage entirely — replace with comment
    (re.compile(r"^.*\b(Brace|BraceBetweenPoints|ArcBrace)\b.*$", re.MULTILINE),
     "# [sanitized] Brace removed — not supported",
     "Remove Brace usage"),

    # Remove .get_text(...) calls that pass font_size (the root cause of the reported error)
    (re.compile(r"\.get_text\(([^)]*?),?\s*font_size\s*=\s*\d+[^)]*\)"),
     ".get_text(\\1)",
     "Strip font_size from get_text()"),

    # Remove .get_tex(...) calls entirely — uses LaTeX
    (re.compile(r"\.get_tex\([^)]*\)"),
     '.get_text("label")',
     "Replace get_tex with get_text"),

    # Strip font_size kwarg from .next_to() calls
    (re.compile(r"(\.next_to\([^)]*?),\s*font_size\s*=\s*\d+"),
     "\\1",
     "Strip font_size from next_to()"),

    # Strip font_size kwarg from .move_to() calls
    (re.compile(r"(\.move_to\([^)]*?),\s*font_size\s*=\s*\d+"),
     "\\1",
     "Strip font_size from move_to()"),

    # Replace Tex(...) with Text(...)
    (re.compile(r"\bTex\("),
     "Text(",
     "Replace Tex() with Text()"),

    # Replace MathTex(...) with Text(...)
    (re.compile(r"\bMathTex\("),
     "Text(",
     "Replace MathTex() with Text()"),

    # Replace BulletedList(...) with VGroup(...)
    (re.compile(r"\bBulletedList\("),
     "VGroup(",
     "Replace BulletedList() with VGroup()"),

    # Replace Code(...) with Text(..., font="Courier New")
    (re.compile(r"\bCode\("),
     'Text(',
     "Replace Code() with Text()"),
]


def _inject_camera_setup(script: str) -> str:
    """Inject a camera/frame setup at the top of construct() to ensure content stays in frame."""
    if "frame_width" in script or "camera" in script:
        return script

    config_block = '''
    def setup(self):
        # Ensure consistent safe viewport
        self.camera.background_color = "#1a1a2e"
'''
    script = script.replace(
        "    def construct(self):",
        config_block + "    def construct(self):",
        1,
    )
    return script


def _sanitize_manim_script(script: str) -> str:
    """Apply safety sanitization to LLM-generated Manim code.

    Catches common LLM mistakes that violate Manim API constraints,
    such as passing font_size to methods that don't support it,
    or using forbidden classes like Brace/Tex/MathTex.
    """
    original = script
    applied = []

    for pattern, replacement, desc in _SANITIZE_RULES:
        new_script = pattern.sub(replacement, script)
        if new_script != script:
            applied.append(desc)
            script = new_script

    if applied:
        logger.info("[concept-manim] Sanitized script — applied: %s", ", ".join(applied))
    else:
        logger.info("[concept-manim] Script passed sanitization without changes")

    return script


def generate_concept_manim(
    prompt: str,
    mood: str = "friendly",
    level: str = "beginner",
) -> ConceptManimResult:
    """Generate a constrained single-scene Manim animation for a concept/algo."""
    from .scripts import _chat

    logger.info("[concept-manim] Generating single-scene Manim for concept/algo")

    user_msg = (
        f"Experience level: {level}\n"
        f"Mood/tone: {mood}\n\n"
        f"Concept to explain visually:\n{prompt}"
    )

    raw = _chat(
        system=_SYSTEM_PROMPT,
        user=user_msg,
        temperature=0.4,
    )

    # Parse tags
    manim = re.search(r"<manim_script>\s*(.*?)\s*</manim_script>", raw, re.DOTALL)
    intro = re.search(r"<intro>\s*(.*?)\s*</intro>", raw, re.DOTALL)
    info = re.search(r"<info>\s*(.*?)\s*</info>", raw, re.DOTALL)
    outro = re.search(r"<outro>\s*(.*?)\s*</outro>", raw, re.DOTALL)

    if not manim:
        raise ValueError(f"Concept Manim response missing <manim_script> tag.\nPreview:\n{raw[:500]}")

    sanitized_script = _sanitize_manim_script(manim.group(1).strip())
    sanitized_script = _inject_camera_setup(sanitized_script)

    result = ConceptManimResult(
        manim_script=sanitized_script,
        intro=intro.group(1).strip() if intro else "Let's explore this concept visually.",
        info=info.group(1).strip() if info else "",
        outro=outro.group(1).strip() if outro else "That's the key idea!",
    )

    logger.info("[concept-manim] Generated script: %d chars, intro: %d, info: %d, outro: %d",
                len(result.manim_script), len(result.intro), len(result.info), len(result.outro))
    return result
