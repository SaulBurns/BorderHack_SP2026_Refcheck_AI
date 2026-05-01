# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (run from `backend/`)

```bash
# First-time setup
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Build FAISS index (required before first run; produces data/indices/basketball/rules.faiss)
python scripts/build_faiss.py

# Start production backend (real pipeline)
ANTHROPIC_API_KEY=sk-ant-... CORS_ORIGINS=http://localhost:3000 \
  uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
source venv/bin/activate
pytest tests/

# Run a single test
pytest tests/test_schemas.py::test_adjudicator_output_roundtrip -v

# Syntax/import check (no venv needed for this quick check)
python3 -m compileall app/
```

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev          # http://localhost:3000
npm run build        # production build check
```

### Local env file

`frontend/.env.local` must contain:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Architecture

This is a multi-agent AI pipeline for reviewing sports officiating calls. A user uploads a video clip; the backend runs a 4-agent pipeline and returns a structured verdict; the frontend displays it.

### Agent pipeline (`backend/app/`)

All agents are `async` and use `anthropic.AsyncAnthropic`. The pipeline is orchestrated in `app/agents/pipeline.py:analyze_clip()` which the FastAPI route calls directly.

```
analyze_clip(video_path, sport, original_call, client)
  │
  ├─ perceive()          app/perception/agent.py
  │    ffmpeg extracts 10 evenly-spaced frames → Claude vision (claude-sonnet-4-5)
  │    → EventDescription (structured JSON, no verdict)
  │
  ├─ retrieve_rules()    app/rag/retriever.py
  │    sentence-transformers embeds the event summary
  │    FAISS inner-product search over data/indices/{sport}/rules.faiss
  │    → list[RuleChunk] (top 5)
  │
  ├─ adjudicate()        app/agents/adjudicator.py
  │    asyncio.gather → two Claude instances in parallel
  │    Adjudicator A: conservative (temp=0.2), defaults to fair_call
  │    Adjudicator B: skeptical   (temp=0.7), challenges the ref
  │    → (AdjudicatorOutput, AdjudicatorOutput)
  │
  └─ reconcile()         app/agents/adjudicator.py
       agree  → that verdict, averaged confidence
       disagree → INCONCLUSIVE, damped confidence
       poor perception confidence → forced INCONCLUSIVE
       → FinalVerdict
```

### Data contracts (`backend/app/models/schemas.py`)

All inter-agent types are Pydantic v2 models. `frontend/src/lib/types.ts` mirrors them in TypeScript — **keep the two files in sync when changing schemas**. The test suite (`backend/tests/test_schemas.py`) covers schema validation; run it after any schema change.

Key types: `EventDescription` → `RuleChunk` → `AdjudicatorOutput` → `FinalVerdict` → `AnalyzeResponse`

### FAISS index bootstrap

There is no PDF in the repo. `backend/data/indices/basketball/rules.json` contains 20 hand-authored NBA rule chunks. `backend/scripts/build_faiss.py` reads that JSON and writes `rules.faiss` (gitignored binary). `backend/build.sh` runs this automatically on Render. Locally, run `python scripts/build_faiss.py` once after setup. The retriever uses `@lru_cache` so the index loads once per process. To add or edit rules, edit `rules.json` and rebuild.

### FastAPI entrypoint (`backend/app/api/main.py`)

- `GET /api/health` — Render healthcheck
- `POST /api/analyze` — multipart: `file` (UploadFile) or `clip_url` (str), `sport`, `original_call`; writes to a `tempfile.TemporaryDirectory` then calls `analyze_clip()`; CORS origins read from `CORS_ORIGINS` env var (comma-separated)

`backend/main.py` is an older mock entrypoint using `services/mock_analyzer.py`. It is not used in production. The Render start command targets `app.api.main:app`.

### Frontend (`frontend/`)

Next.js 15 App Router. Six screens in `src/app/screens/` — `Home`, `Upload`, `Verdict`, `Feed`, `Leaderboard`, `RefProfile` — each has a thin page wrapper in `src/app/<route>/page.tsx`.

The only file that talks to the backend is `src/lib/api.ts`. It reads `NEXT_PUBLIC_API_BASE` (must be set at **build time** for Vercel, not just runtime). `analyzeClip()` POSTs multipart form data; the verdict is cached in `sessionStorage` keyed by `clip_id` so the verdict page survives a reload without re-calling the API.

### Deployment

- **Backend → Render**: `render.yaml` at repo root; rootDir=`backend`; build=`bash build.sh`; start=`uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
- **Frontend → Vercel**: root directory=`frontend`; framework auto-detected as Next.js; env var=`NEXT_PUBLIC_API_BASE`

## Key Constraints

- Do not change `backend/app/models/schemas.py` without updating `frontend/src/lib/types.ts` to match.
- The model strings `claude-sonnet-4-5` in `perception/agent.py` and `agents/adjudicator.py` are intentionally not updated to 4.6 yet — check before changing.
- `retrieve_rules()` resolves `data/indices/{sport}/` relative to the process working directory. The process must start from `backend/`.
- Render free tier sleeps after 15 min inactivity. Hit `/api/health` before a demo to warm up.
