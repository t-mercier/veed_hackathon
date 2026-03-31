"""
Mistral script generation for code/concept explanations.

Given a prompt, returns:
- A Manim animation script (scene class `GeneratedScene`)
- A 3-part narration (intro / info / outro) matching Bote's TTSScript format

The intro and outro are spoken by the avatar (on-screen talking head).
The info part is the voiceover narrated during the Manim animation.

NOTE: Repo explanation now uses the separate repo_analysis/repo_storyboard pipeline.
This module only handles code snippet / concept explanations.
"""

import logging
import re
from dataclasses import dataclass
from config import settings

logger = logging.getLogger(__name__)


# ── LLM client (Mistral) ──────────────────────────────────────────────────────

def _chat(system: str, user: str, temperature: float = 0.4) -> str:
    """Send a chat completion via Mistral and return the response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    from mistralai.client import Mistral
    if not settings.mistral_api_key:
        raise RuntimeError("No LLM key set — add MISTRAL_API_KEY to .env")
    client = Mistral(api_key=settings.mistral_api_key)
    resp = client.chat.complete(model="mistral-small-latest", messages=messages)
    logger.info("LLM: Mistral/mistral-small-latest")
    return resp.choices[0].message.content.strip()

@dataclass
class TTSScript:
    """Mirrors src/veed.py TTSScript — Bote consumes this for TTS + avatar."""
    intro: str
    info: str
    outro: str


_SYSTEM_PROMPT = """You are an expert Manim animator and computer science educator.

Given a topic or code snippet, experience level, and mood, return TWO things:
1. A complete, runnable Manim (Community Edition 0.20) Python script
2. A 3-part narration script:
   - INTRO: 1–2 sentences the avatar says on camera BEFORE the animation. Greet the viewer and introduce the topic.
   - INFO: The voiceover narrated DURING the animation. Explain what's appearing on screen step by step.
   - OUTRO: 1–2 sentences the avatar says on camera AFTER the animation. Summarize the takeaway.

MANIM RULES (follow EXACTLY — any violation will crash the render):
- The Scene class MUST be named exactly `GeneratedScene`
- Import only: `from manim import *`
- Do NOT use MathTex, Tex, or any LaTeX — use Text() for ALL text
- Do NOT use the Code() class — display code snippets using Text() with font="Courier New"
  Example: Text("def factorial(n):", font="Courier New", font_size=24)
  For multi-line code: stack multiple Text() objects in a VGroup with .arrange(DOWN, aligned_edge=LEFT)
- Do NOT use external images or custom fonts other than "Courier New"
- Do NOT use BulletedList() — use VGroup of Text() objects instead
- Target 30–45 seconds total runtime; keep it tight
- Use clear colours: WHITE, YELLOW, BLUE, GREEN, RED on dark background
- Show one concept at a time with labels and annotations
- ALWAYS call self.wait(1) between major steps
- Keep animations simple: Write, FadeIn, FadeOut, Create, GrowArrow, Transform
- SurroundingRectangle ONLY accepts a single Mobject or VGroup — NEVER pass a Python list or slice
  WRONG: SurroundingRectangle(code_lines[0:3], ...)
  RIGHT: SurroundingRectangle(VGroup(*code_lines[0:3]), ...)
- VGroup slicing returns a list — always wrap with VGroup(*...) before passing to any Manim function
- Store each code line as a separate Text() variable; group with VGroup(...).arrange(DOWN, aligned_edge=LEFT)

SAFE MANIM OBJECTS (use only these unless you are 100% sure of the API):
- Text, VGroup, Arrow, Rectangle, Circle, Square, Line, Dot
- Axes (for graphs), NumberLine
- SurroundingRectangle (single Mobject/VGroup only — see rule above), Underline

NARRATION RULES:
- Plain spoken English, no markdown, no special characters
- INTRO: ~20 words, conversational greeting + topic introduction
- INFO: ~100–150 words, matches the visual timeline of the animation
- OUTRO: ~20 words, clear takeaway or summary

Return ONLY this exact format:

<manim_script>
[complete Python code]
</manim_script>

<intro>
[avatar intro speech]
</intro>

<info>
[animation voiceover]
</info>

<outro>
[avatar outro speech]
</outro>"""


def _build_user_prompt(prompt: str, mode: str, level: str, mood: str) -> str:
    return f"Mode: {mode}\nExperience level: {level}\nMood/tone: {mood}\n\nInput:\n{prompt}"


def _parse(content: str) -> dict:
    manim = re.search(r"<manim_script>\s*(.*?)\s*</manim_script>", content, re.DOTALL)
    intro = re.search(r"<intro>\s*(.*?)\s*</intro>", content, re.DOTALL)
    info = re.search(r"<info>\s*(.*?)\s*</info>", content, re.DOTALL)
    outro = re.search(r"<outro>\s*(.*?)\s*</outro>", content, re.DOTALL)

    if not manim:
        raise ValueError(f"Response missing <manim_script> tag.\nPreview:\n{content[:500]}")
    if not intro or not info or not outro:
        # Fallback: try old single <narration> tag and split heuristically
        narration = re.search(r"<narration>\s*(.*?)\s*</narration>", content, re.DOTALL)
        if narration:
            text = narration.group(1).strip()
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            return {
                "manim_script": manim.group(1).strip(),
                "tts_script": TTSScript(
                    intro=sentences[0] if sentences else "",
                    info=" ".join(sentences[1:-1]) if len(sentences) > 2 else " ".join(sentences),
                    outro=sentences[-1] if len(sentences) > 1 else "",
                ),
            }
        raise ValueError(f"Response missing narration tags.\nPreview:\n{content[:500]}")

    return {
        "manim_script": manim.group(1).strip(),
        "tts_script": TTSScript(
            intro=intro.group(1).strip(),
            info=info.group(1).strip(),
            outro=outro.group(1).strip(),
        ),
    }


def generate_scripts(
    prompt: str,
    mode: str = "code",
    level: str = "beginner",
    mood: str = "friendly",
) -> dict:
    """Returns {"manim_script": str, "tts_script": TTSScript}."""
    logger.info("Calling LLM via %s for concept/code script", settings.llm_provider)
    raw = _chat(
        system=_SYSTEM_PROMPT,
        user=_build_user_prompt(prompt, mode, level, mood),
        temperature=0.5,
    )
    return _parse(raw)
