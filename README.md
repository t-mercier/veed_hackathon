# Animated Explainer Studio

AI-powered visual explanations for **code snippets**, **programming concepts**, and **GitHub repositories**.

Instead of forcing users to reconstruct a system from raw code, Animated Explainer Studio turns technical content into a guided visual walkthrough.

---

## Why we built this

Understanding code is still one of the slowest parts of software development.

When you open a new function or a new repository, you usually have to:

- read several files manually
- infer structure from naming and imports
- rebuild the system mentally
- guess how components interact

At the same time, AI is making code generation faster and more accessible.

That shifts the skill that matters most:

**the real challenge is no longer only writing code — it is understanding architecture, design decisions, and system flow.**

Animated Explainer Studio is designed for that shift.

---

## What problem it solves

This project helps reduce the time it takes to understand:

- a function
- a code snippet
- a concept such as arrays, pointers, or memory allocation
- a complete GitHub repository architecture

Instead of a static explanation, the user gets a **visual and narrated walkthrough**.

---

## Target audience

We built this for:

- developers onboarding into a new codebase
- students learning programming concepts
- engineers reviewing unfamiliar logic quickly
- hackathon teams and technical interview candidates
- anyone who wants a faster mental model of how code works

---

## Product modes

### 1. Prompt Mode

Prompt Mode explains:

- code snippets
- functions or methods
- technical concepts and algorithms

Depending on the request, the backend routes the input into the right explanation path:

- **Code explanation** → structured visual scenes
- **Concept / algorithm explanation** → constrained animation path for concepts that benefit from visual motion

Examples:

- “Explain this function”
- “Explain how binary search works”
- “Explain how malloc and free work”
- “Explain arrays and indexing”

If a GitHub repo link is included, it is used as **context** to better understand the snippet, without switching into full repository mode.

---

### 2. Repo Mode

Repo Mode takes a GitHub repository URL and explains the project as a system.

Instead of listing folders, it reconstructs the architecture:

- main components
- responsibilities
- relationships
- system flow
- teaching sequence

The result is a scene-by-scene visual explanation of the repository.

This is the strongest “wow” mode of the project.

---

## How it works

### Prompt Mode flow

1. User submits a prompt, snippet, or concept
2. Backend analyzes the request
3. The system decides whether the input is:
   - a code explanation
   - or a concept / algorithm explanation
4. The explanation is generated
5. A narrated video is produced
6. The user can watch or download the final result

---

### Repo Mode flow

1. User submits a GitHub repository URL
2. Repository content is ingested and summarized
3. AI extracts:
   - architectural components
   - relationships
   - flows
4. A second step turns that into a teaching storyboard
5. The frontend renders this as a scene-based visual walkthrough
6. Narration and video output complete the experience

---

## Design approach

We intentionally avoided treating the repository as a raw file tree.

Instead, the system converts technical input into **intermediate structured representations** first.

### For Repo Mode

The pipeline is roughly:

- repository ingestion
- architecture extraction
- storyboard generation
- narration assembly
- scene rendering

This lets us explain a project **as a system**, not just as a list of folders.

### For Prompt Mode

The system distinguishes between:

- code that benefits from structured scene breakdowns
- concepts and algorithms that benefit from animated visualization

This gives us a more appropriate explanation style depending on what the user is trying to learn.

---

## Tech stack

### Frontend

- **Vite**
- **React**
- **TypeScript**
- **Tailwind CSS**
- **React Flow**

The frontend is responsible for rendering structured, scene-based explanations in a clean visual way.

---

### Backend

- **FastAPI**
- **Python**
- **Mistral**
- **Manim**
- **Runware**
- **fal.ai / VEED Fabric**
- **ffmpeg**
- **Supabase**

The backend handles:

- prompt and repo analysis
- architecture/storyboard generation
- narration assembly
- TTS / avatar video generation
- final media composition

---

## Why React Flow

For repository explanations, we moved away from free-form generated animation scripts and toward a deterministic scene renderer.

React Flow gives us:

- stable layouts
- step-by-step focus
- highlighted relationships
- clearer architectural explanations
- more predictable visual output for demos

This made Repo Mode significantly more robust and more readable.

---

## Why Manim is still used selectively

Manim remains useful for certain concept-heavy explanations where motion matters, for example:

- memory allocation
- arrays
- pointer-like behavior
- algorithm progression

To avoid unstable overlapping animations, this path is intentionally constrained.

---

## Monetization idea

We designed the product with a **freemium model** in mind.

### Free tier
- basic prompt explanations
- simple repo exploration
- lightweight use cases

### Premium tier
- deeper analysis
- more advanced concept explanations
- richer visualizations
- enhanced educational modes

This makes the product accessible while keeping a clear path to monetization.

---

## Repository structure

```text
.
├── client/
├── server/
├── supabase/
├── .env.template
├── package.json
└── requirements.txt
