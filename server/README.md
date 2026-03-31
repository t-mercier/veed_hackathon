# Animated Explainer Studio — Server

AI-powered animated explanations for code snippets and GitHub repositories.

## Architecture

Two pipelines depending on input:

### Repo Explainer (GitHub URL → React Flow)
```
POST /generate  ←  GitHub repo URL
     ↓
  GitHub API → repo content ingestion
     ↓
  Mistral → Architecture JSON (components, relationships, flows)
     ↓
  Mistral → Storyboard JSON (5–7 teaching scenes)
     ↓
  Narration assembly (per-scene)
     ↓
  Response: { architecture, storyboard, narration, tts_script }
     ↓
  Frontend: React Flow scene-driven renderer at /repo/:jobId
```

### Code Explainer (snippet/concept → Manim video)
```
POST /generate  ←  code snippet or concept prompt
     ↓
  Mistral → manim_script + TTSScript(intro, info, outro)
     ↓
  Manim render → animation.mp4
     ↓
  VEED pipeline → intro.mp4 + outro.mp4 (avatar) + info.mp3 (TTS)
     ↓
  ffmpeg merge → final.mp4
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/generate` | Start generation job (returns `job_id`) |
| `GET`  | `/jobs/{id}` | Poll job status + results |
| `GET`  | `/health` | Health check |
| `GET`  | `/files/{job_id}/*` | Serve rendered files |

## Setup

```bash
cd server
chmod +x setup_env.sh && ./setup_env.sh
cp .env.template .env
# Fill in: MISTRAL_API_KEY, GITHUB_TOKEN, RUNWARE_API_KEY, FAL_KEY
```

### System dependencies (macOS)
```bash
brew install cairo pango pkg-config ffmpeg
```

## Run

```bash
# Option 1: direct
cd server
manim-env/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Option 2: shell alias (add to ~/.zshrc)
alias explainer-start='...'   # see aliases below
```

### Shell aliases (add to ~/.zshrc)

```bash
explainer-start() {
  lsof -i :8000 | awk 'NR>1{print $2}' | sort -u | xargs kill -9 2>/dev/null
  cd ~/my_projects/hackathon/animated-explainer-studio/server
  nohup manim-env/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 \
    --log-level info > /tmp/explainer-server.log 2>&1 &
  echo "Server started (PID $!) — logs: /tmp/explainer-server.log"
}
alias explainer-stop='lsof -i :8000 | awk "NR>1{print \$2}" | sort -u | xargs kill -9 2>/dev/null && echo "Stopped"'
alias explainer-logs='tail -f /tmp/explainer-server.log'
```

## Frontend

```bash
cd client
npm install
npm run dev   # → http://localhost:5173
```

Repo explainer results are rendered at: `http://localhost:5173/repo/<job_id>`

## Test

```bash
# Repo explanation (React Flow)
curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"https://github.com/tmercier/42_fdf","mood":"friendly","level":"beginner"}' \
  | python3 -m json.tool

# Code explanation (Manim video)
curl -s -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Explain how binary search works","mode":"concept","level":"beginner"}' \
  | python3 -m json.tool

# Poll job
curl -s http://localhost:8000/jobs/<job_id> | python3 -m json.tool
```

## Project Structure

```
server/
├── main.py                  # FastAPI app, CORS, /files mount
├── config.py                # API keys (Mistral, GitHub, Runware, fal)
├── models.py                # Request/response schemas
├── database.py              # OUTPUT_DIR + job_dir()
├── pipeline/
│   ├── scripts.py           # Mistral → Manim script + TTS (code path)
│   ├── manim_render.py      # Async Manim subprocess
│   ├── enrich.py            # URL/GitHub repo content ingestion
│   ├── repo_models.py       # Pydantic: Architecture, Storyboard, Scene, Narration
│   ├── repo_analysis.py     # Mistral → Architecture JSON (repo path)
│   ├── repo_storyboard.py   # Mistral → Storyboard scenes (repo path)
│   ├── repo_narration.py    # Narration assembly + TTS bridge (repo path)
│   ├── veed_pipeline.py     # Runware TTS + fal.ai avatar (Bote)
│   └── final_merge.py       # ffmpeg video assembly (Bote)
└── routers/
    ├── generate.py          # POST /generate, GET /jobs/{id}
    └── health.py            # GET /health
```

## Response Format

### Repo job (job_type: "repo")
```json
{
  "job_id": "uuid",
  "status": "done",
  "job_type": "repo",
  "architecture": {
    "repo_name": "42_fdf",
    "summary": "3D wireframe renderer",
    "components": [{"id": "...", "label": "...", "type": "...", "responsibility": "..."}],
    "relationships": [{"id": "...", "from": "...", "to": "...", "kind": "...", "label": "..."}],
    "flows": [{"id": "...", "title": "...", "steps": ["..."]}]
  },
  "storyboard": {
    "scenes": [{"id": "...", "title": "...", "narration": "...", "visible_components": [...]}]
  },
  "narration": {
    "intro": "...",
    "scenes": [{"scene_id": "...", "narration": "..."}],
    "outro": "..."
  },
  "tts_script": {"intro": "...", "info": "...", "outro": "..."}
}
```

### Code job (job_type: "code")
```json
{
  "job_id": "uuid",
  "status": "done",
  "job_type": "code",
  "animation_url": "http://localhost:8000/files/{job_id}/animation.mp4",
  "final_url": "http://localhost:8000/files/{job_id}/final.mp4",
  "tts_script": {"intro": "...", "info": "...", "outro": "..."}
}
```

## API Keys

| Key | Source | Used for |
|-----|--------|----------|
| `MISTRAL_API_KEY` | console.mistral.ai | Script/architecture generation |
| `GITHUB_TOKEN` | github.com/settings/tokens | Repo ingestion (higher rate limit) |
| `RUNWARE_API_KEY` | runware.ai | TTS audio generation |
| `FAL_KEY` | fal.ai | Avatar video generation (VEED Fabric) |

