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

### AI provider abstraction

The four-agent pipeline talks to LLMs **only** through the provider interface in `backend/services/ai/`. The rest of the app never knows whether it is speaking to Anthropic, Gemini, or the mock.

**Where providers live:**

```
backend/services/ai/
  provider.py                  # AIProvider ABC + neutral message content (text/image parts)
  factory.py                   # get_provider() — selects by AI_PROVIDER, raises on invalid
  providers/
    anthropic_provider.py      # Claude Messages API (HTTP)
    gemini_provider.py         # Google GenAI SDK (google-genai, lazy-imported)
    mock_provider.py           # demo-safe, no network
```

**The interface** (`AIProvider`): `send_messages(system_prompt, user_content, temperature, max_tokens) -> str`, `supports_vision()`, `provider_name()`, and an `is_mock` property.

**How the pipeline interacts with providers:** `ai_analyzer.py` resolves the active provider once via `get_provider()` (from `AI_PROVIDER`). If `provider.is_mock`, it takes the canned demo path (`_mock_ai_result`, unchanged output). Otherwise the three real agents (`_perception_agent`, `_retrieval_agent`, `_adjudicator_agent`) send their turns through the single `_send_messages()` seam, which delegates to `provider.send_messages()`. Message content is provider-neutral: callers pass a string or a list of `text_part(...)` / `image_part(path)` parts, and each provider translates them into its own wire format. The raw text reply is parsed by the **shared** `_extract_json()` in `ai_analyzer.py` — parsing is never duplicated per provider.

**Why provider-specific logic must never leak into `ai_analyzer.py`:** the analyzer owns the *pipeline* (agents, reconciliation, diagnostics), not vendor plumbing. Keeping HTTP/SDK/auth/model-name/image-encoding details inside the provider classes is what makes providers swappable by env var alone and keeps the pipeline untouched when a backend changes.

**Environment configuration:** `AI_PROVIDER` selects the provider (`mock` | `anthropic` | `gemini`; default `mock`; invalid values raise a clear error). `anthropic` needs `ANTHROPIC_API_KEY` (model override: `AI_MODEL`, default `claude-sonnet-4-5`). `gemini` needs `GEMINI_API_KEY` and the `google-genai` package (model override: `GEMINI_MODEL`, default `gemini-2.5-flash`). Missing keys degrade to the mock fallback with the reason surfaced in diagnostics; an unsupported `AI_PROVIDER` value fails loudly.

**Adding a future provider** (OpenAI, Azure, Grok, Ollama, …): (1) create one class implementing `AIProvider` under `providers/`, (2) register it in `factory._PROVIDERS`. The four-agent pipeline requires zero changes. Design principle for contributors: a provider only knows how to turn a system prompt + neutral content + temperature/max_tokens into a text reply — it must not import `ai_analyzer`, know about agents, or reshape JSON.

### Hybrid perception grounding (YOLO tracked evidence)

**Principle:** YOLO tracked detections are *supporting evidence only*. Claude Vision remains the semantic authority; detections ground the adjudicators' reasoning but never replace it, and never change the frontend API contract.

**Detector paths** (`DETECTOR` env): `claude_vision` (semantic only, `detections=None`), `yolov8` (detections only), `hybrid` (Claude perception + YOLO detections). `hybrid` degrades gracefully: if YOLO inference fails (e.g. ultralytics missing, bad frame), `HybridDetector.detect` keeps Claude's perception and drops tracking (`detections=None`) instead of failing the analysis — the four-agent pipeline still runs, and diagnostics show `detections_present=False`.

**How detections influence the verdict** (all in `_run_four_agent_pipeline` / `_build_response`, basketball-scoped):
- `services/extractors/basketball_vision.py:summarize_tracked_evidence()` turns `RawDetections` into a compact evidence dict: offensive/defender `track_id`s, per-frame `possession_timeline`, `possession_changes`, ball-handler + defender movement, **ball's own `ball_movement`** (from `track_ball`, independent of any player), and a `tracking_confidence ∈ [0,1]`.
- This evidence is attached to **both** adjudicator prompts (`_adjudicator_agent`, `TRACKED DETECTION EVIDENCE` section) alongside `sport_details` — computed once, passed to both.
- `_reconcile` takes the evidence's `tracking_confidence` and applies a bounded ±0.05 nudge to the final confidence **only when the adjudicators agree** (calibrate, never decide).
- `_frontend_perception` maps detection-derived signals into `sport_details` (the frontend block) — enrichment only; every legacy field is preserved.

**Single-scan dedup:** the controlling player per frame is computed exactly once via `_scan_controllers`; `possession_status`, `identify_primary_defender`, `analyze_basketball`, and `summarize_tracked_evidence` all derive from that shared scan instead of re-scanning the frames.

**Influence diagnostics:** `_diagnostics_payload` reuses the already-computed `tracked_evidence` (no recomputation) to expose `yolo_influenced`, `tracked_evidence_present`, `tracking_confidence`, `possession_summary`, `defender_tracked`, `ball_trajectory_present`, and `influenced_reconciliation` — so it is visible when and how YOLO shaped a decision.

**Scope note:** the tracked-evidence layer is basketball-only for now (gated on `sport == "basketball"`); other sports get Claude-only perception, unchanged.

### Frontend (`frontend/`)

Next.js 15 App Router. Six screens in `src/app/screens/` — `Home`, `Upload`, `Verdict`, `Feed`, `Leaderboard`, `RefProfile` — each has a thin page wrapper in `src/app/<route>/page.tsx`.

The only file that talks to the backend is `src/lib/api.ts`. It reads `NEXT_PUBLIC_API_BASE` (must be set at **build time** for Vercel, not just runtime). `analyzeClip()` POSTs multipart form data; the verdict is cached in `sessionStorage` keyed by `clip_id` so the verdict page survives a reload without re-calling the API.

### Deployment

- **Backend → Render**: `render.yaml` at repo root; rootDir=`backend`; build=`bash build.sh`; start=`uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
- **Frontend → Vercel**: root directory=`frontend`; framework auto-detected as Next.js; env var=`NEXT_PUBLIC_API_BASE`

## Key Constraints

- Do not change `backend/app/models/schemas.py` without updating `frontend/src/lib/types.ts` to match.
- The Anthropic model default `claude-sonnet-4-5` lives in `backend/services/ai/providers/anthropic_provider.py` (`DEFAULT_MODEL`), overridable via `AI_MODEL`. It is intentionally not updated to 4.6 yet — check before changing. Provider-specific model names belong in the provider classes, never in `ai_analyzer.py`.
- `retrieve_rules()` resolves `data/indices/{sport}/` relative to the process working directory. The process must start from `backend/`.
- Render free tier sleeps after 15 min inactivity. Hit `/api/health` before a demo to warm up.
