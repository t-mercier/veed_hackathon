# Animated Explainer Studio

> ⭐ If you find this useful, please star the repo — it helps others discover the project!

AI-powered visual explanations for **code snippets**, **programming concepts**, and **GitHub repositories**.

Instead of forcing users to reconstruct a system from raw code, Animated Explainer Studio turns technical content into a guided visual walkthrough.

---

## Quick start (local)

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **ffmpeg** — `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
- **System deps for Manim** — `brew install cairo pango pkg-config` (macOS)

### 1. Clone and install

```bash
git clone https://github.com/t-mercier/code-visual-explainer.git
cd code-visual-explainer

# Backend
cd server
cp .env.template .env          # fill in your API keys
pip install -r ../requirements.txt

# Frontend
cd ../client
npm install
```

### 2. Configure API keys

Edit `server/.env` with at minimum:

```
MISTRAL_API_KEY=your_key       # required — LLM for script generation
```

Optional (for TTS & avatar videos):

```
FAL_KEY=your_key               # fal.ai — avatar video generation
RUNWARE_API_KEY=your_key       # Runware — text-to-speech
```

### 3. Run

Open **two terminals**:

```bash
# Terminal 1 — backend (FastAPI on port 8000)
cd server
uvicorn main:app --reload

# Terminal 2 — frontend (Vite dev server on port 5173)
cd client
npm run dev
```

Then open **http://localhost:5173** in your browser.

### 4. Use

- **Home page** — paste a concept, code snippet, or GitHub repo URL and generate an explanation
- **Concepts** — browse pre-made demo videos for common topics
- **Studio** — full controls: choose avatar, voice, mood, level, then generate

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

## Product modes

### 1. Prompt Mode

Explains code snippets, functions, and technical concepts/algorithms.

Depending on the request, the backend routes the input into the right explanation path:

- **Code explanation** → structured visual scenes
- **Concept / algorithm explanation** → constrained animation (Manim)

Examples: "Explain how binary search works", "Explain how malloc and free work"

### 2. Repo Mode

Takes a GitHub repository URL and explains the project as a system:
components, responsibilities, relationships, and flow — rendered as a scene-based visual walkthrough.

---

## Tech stack

### Frontend

- **Vite** + **React** + **TypeScript**
- **Tailwind CSS**
- **React Flow** — scene-based visual walkthroughs

### Backend

- **FastAPI** + **Python**
- **Mistral** — LLM for script/architecture generation
- **Manim** — math/algorithm animations
- **Runware** — text-to-speech
- **fal.ai / VEED Fabric** — avatar video generation
- **ffmpeg** — media composition

---

## Repository structure

```text
.
├── client/          # React frontend (Vite)
├── server/          # FastAPI backend
│   ├── pipeline/    # Analysis, storyboard, narration, rendering
│   ├── routers/     # API endpoints
│   └── .env.template
├── package.json     # Root scripts (dev/build shortcuts)
└── requirements.txt # Python dependencies
```

---

## Contributing

We welcome contributions! Check out the [Contributing Guide](CONTRIBUTING.md) and the [open issues](https://github.com/t-mercier/code-visual-explainer/issues).

**Good starting points:**
- Issues labeled [`good first issue`](https://github.com/t-mercier/code-visual-explainer/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- Issues labeled [`help wanted`](https://github.com/t-mercier/code-visual-explainer/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22)

## License

[MIT](LICENSE)
