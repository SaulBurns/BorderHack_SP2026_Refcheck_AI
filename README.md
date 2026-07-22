# RefCheck AI

**Upload a sports clip + the call the ref made → get a verdict (fair / bad /
inconclusive) with confidence, the cited rule, and the reasoning behind it.**

RefCheck AI is a **three-agent AI pipeline** for reviewing officiating calls: it *sees*
the play, then has **two independent adjudicators** argue it from opposite biases —
each handed the sport's **complete rulebook** — before **reconciling** them into a final
verdict. It runs on **Anthropic, Gemini, or fully offline** — switching is a single
environment variable.

### 🏀 For judges — start here

- **[Judge cheat sheet](docs/JUDGE_CHEAT_SHEET.md)** — the pitch, differentiators, and what to look at (1 page).
- **[Demo walkthrough](docs/DEMO_WALKTHROUGH.md)** — three ways to demo, no API keys required.
- **[Architecture](docs/ARCHITECTURE.md)** — diagrams + module map.
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** · **[Deployment checklist](docs/DEPLOYMENT_CHECKLIST.md)** · **[Production deployment guide](docs/PRODUCTION_DEPLOYMENT.md)**

Fastest look (offline, no keys):

```bash
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/run_demo_suite.py            # 10 curated scenarios → metrics report
```

### Stack

- Frontend: Next.js 15 (App Router) — Verdict screen with an **AI reasoning overlay**
- Backend: FastAPI — synchronous three-agent pipeline off the event loop
- Sports are **plugins** (`backend/sports/`): each sport owns its prompts, rules, tracking, and game context behind a `Sport` interface; the pipeline never checks `sport == "basketball"`. **Basketball**, **soccer** (Sprint 10), **hockey** (Sprint 11), and **lacrosse** (Sprint 12) all ship as full plugins; any unregistered sport falls back to a generic Claude-only plugin. Adding a sport = one plugin package + one registry line.
- Analysis: ffmpeg frame extraction + provider-agnostic Claude/Gemini pipeline with mock fallback + optional YOLO tracking
- Evaluation: offline benchmarking harness (accuracy/precision/recall/F1, calibration, latency, provider comparison)
- Optional persistence: Supabase Postgres + Supabase Storage

Supported providers (switching is a single env change — no code changes):

- `AI_PROVIDER=mock` for local demos without paid keys
- `AI_PROVIDER=anthropic` with `ANTHROPIC_API_KEY` for the real three-agent pipeline
- `AI_PROVIDER=gemini` with `GEMINI_API_KEY` to run the same pipeline on Google Gemini

Any other value fails loudly at request time instead of silently degrading. See
[CLAUDE.md](CLAUDE.md#ai-provider-abstraction) for the provider architecture and
how to add a new provider.

The three agents are:

1. Perception Agent: watches extracted frames and produces structured observation JSON.
2. Adjudicator A: conservative reviewer that gives the original call benefit of the doubt.
3. Adjudicator B: skeptical reviewer that independently challenges the original call.

Both adjudicators receive the sport's **complete rule corpus** directly in their prompt
(the corpora are small — 6-9 rules per sport — so there is no separate retrieval step).
The backend reconciles both adjudicators into the final verdict.

## First-Time Setup

Run these commands after cloning the repo for the first time.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

For real video analysis, install `ffmpeg` locally:

```bash
brew install ffmpeg
```

Then copy the backend env example:

```bash
cp .env.example .env
```

Keep `AI_PROVIDER=mock` for free local testing. To use the real three-agent pipeline,
pick one provider — **switching providers only requires changing environment variables**:

```bash
# Anthropic (Claude)
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-5        # optional; default: claude-sonnet-4-5
ANTHROPIC_API_KEY=your_key
```

```bash
# Google Gemini (requires: pip install google-genai)
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash     # optional; default: gemini-2.5-flash
GEMINI_API_KEY=your_key
```

The three-agent pipeline is identical across providers — only the model backend changes.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
```

## Run Locally

You need two terminals: one for the backend and one for the frontend.

### Terminal 1: Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- Health check: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- Frontend endpoint: `http://127.0.0.1:8000/api/analyze`

### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

If port `3000` is busy:

```bash
npm run dev -- --port 3001
```

## After Pulling New Updates

After running:

```bash
git pull origin main
```

Update dependencies if package files changed.

### Backend Updates

```bash
cd backend
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

Then restart the backend:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Updates

```bash
cd frontend
npm install
npm run dev
```

If the page looks stale or styles look wrong, stop the dev server with `Ctrl + C`, then run:

```bash
rm -rf .next
npm run dev
```

Then hard refresh the browser:

```text
Cmd + Shift + R
```

## Build Check

Before demoing or deploying, run:

```bash
cd frontend
npm run build
```

This verifies the Next.js app compiles correctly.

For backend syntax/import checks:

```bash
cd backend
source venv/bin/activate
python3 -m compileall main.py rules services
```

## Production readiness (Sprint 15)

The backend ships production hardening — **all additive, no breaking API changes**
(everything is off or backward-compatible by default). Full guide:
**[docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md)**.

- **Auth** — optional API-key auth on the write endpoints (`X-API-Key` / `Bearer`), enabled by setting `API_KEYS`. Off = open (unchanged).
- **Rate limiting** — per-client fixed window on the analyze endpoints, enabled by `RATE_LIMIT_PER_MINUTE`.
- **Structured logging** — JSON logs with `request_id`, path, status, `duration_ms` (`LOG_FORMAT`/`LOG_LEVEL`).
- **Metrics** — `GET /api/metrics` in Prometheus text format (requests, latency, analyses, rate-limit/auth rejections).
- **Health** — `GET /api/health` (liveness, backward-compatible), `GET /api/health/ready` (readiness: provider/ffmpeg/disk), `GET /api/version`.
- **Monitoring** — every response carries an `X-Request-ID` for tracing.
- **Docker** — multi-stage, non-root, `HEALTHCHECK`; `.dockerignore` keeps the image lean and secret-free.
- **Overhead** — the middleware adds ~0.3 ms/request; the analysis pipeline is unchanged (`scripts/prod_overhead_benchmark.py`).

## Deployment

Recommended hackathon deployment:

- Frontend: Vercel
- Backend: Render
- Backend runtime: Docker, so `ffmpeg` is available for frame extraction

### Render Backend

This repo includes `render.yaml` and `backend/Dockerfile`.

On Render:

1. Create a new Blueprint or Web Service from the GitHub repo.
2. Use the backend service from `render.yaml`.
3. Set `FRONTEND_ORIGIN` to your Vercel URL, for example `https://refcheck-ai.vercel.app`.
4. Set `AI_PROVIDER` to `mock`, `anthropic`, or `gemini`.
5. Add `ANTHROPIC_API_KEY` (for `anthropic`) or `GEMINI_API_KEY` (for `gemini`).

Use `mock` until the backend deploy is healthy, then switch to a paid provider.

### Optional Supabase Persistence

Supabase lets uploaded videos and verdicts appear on the Hot Takes page after deployment.

1. Create a Supabase project.
2. Open Supabase SQL Editor.
3. Run the SQL in:

```text
backend/supabase_schema.sql
```

4. Open Supabase Storage.
5. Create a bucket named:

```text
clips
```

6. Make the `clips` bucket public so browser video playback works.
7. In Supabase Project Settings, copy:
   - Project URL
   - Service role key

8. In Render backend environment variables, add:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_CLIPS_BUCKET=clips
SUPABASE_VERDICTS_TABLE=verdicts
```

Do not add the service role key to Vercel. It belongs only on the backend.

After saving the Render env vars, redeploy the backend.

### Vercel Frontend

On Vercel:

1. Set the project root to `frontend`.
2. Add this environment variable:

```bash
NEXT_PUBLIC_API_BASE=https://your-render-backend.onrender.com
```

3. Deploy.

After Vercel deploys, copy the Vercel URL back into Render as `FRONTEND_ORIGIN`.

## Common Issues

### Backend port already in use

```bash
lsof -i :8000
kill -9 PID_NUMBER
```

Then restart:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend port already in use

```bash
cd frontend
npm run dev -- --port 3001
```

### Frontend cannot reach backend

Make sure the backend is running on:

```text
http://127.0.0.1:8000
```

The frontend uses:

```text
http://localhost:8000/api/analyze
```

## Current Demo Flow

1. User opens the Next.js frontend.
2. User uploads a basketball clip.
3. Frontend sends multipart form data to FastAPI.
4. Backend saves the uploaded clip temporarily.
5. Backend extracts representative frames with `ffmpeg`.
6. Perception Agent describes what happened without making a ruling.
7. Backend loads the sport's complete rule corpus and injects it into both adjudicators.
8. Conservative and Skeptical Adjudicator Agents independently rule on the play.
9. Backend reconciles the two adjudicators into one final verdict.
10. If AI is unavailable, the mock analyzer returns a demo-safe verdict.
11. Backend returns a verdict:
   - Fair Call
   - Bad Call
   - Inconclusive
12. Frontend displays confidence, cited rule, reasoning, perception details, and adjudicator results.

## Sponsor Demo Suite

A curated basketball dataset drives a one-command demo. Run it from `backend/`:

```bash
python scripts/run_demo_suite.py
```

This loads `demo_clips/manifest.json` (10 officiating scenarios — charge, blocking
foul, shooting foul, travel, double dribble, out of bounds, goaltending, illegal
screen, verticality, loose-ball foul), runs every clip through the real
`analyze_clip` pipeline, prints a per-clip summary, and writes a polished report to
`demo_reports/demo_report.md` and `demo_reports/demo_report.json`.

Each manifest entry carries metadata (teams, date), an expected verdict, a rule
citation, a confidence expectation, and notes. The report aggregates verdict
accuracy, rule-citation accuracy, confidence-expectation rate, scenario coverage,
verdict distribution, and average confidence.

```bash
# Real pipeline (needs ANTHROPIC_API_KEY + ffmpeg); refuse to degrade to mock:
python scripts/run_demo_suite.py --provider anthropic --detector hybrid --strict-real
# One scenario:
python scripts/run_demo_suite.py --clip-id nba_goaltending_07
```

**Soccer** (Sprint 10), **hockey** (Sprint 11), and **lacrosse** (Sprint 12) each
ship their own curated suite — soccer: foul, offside, handball, penalty, red card,
yellow card, goal; hockey: icing, offside, tripping, cross-checking, boarding,
slashing, hooking; lacrosse: illegal body check, slash, push, crease violation,
offside, loose-ball push:

```bash
python scripts/run_demo_suite.py --manifest demo_clips/soccer_manifest.json
python scripts/run_demo_suite.py --manifest demo_clips/hockey_manifest.json
python scripts/run_demo_suite.py --manifest demo_clips/lacrosse_manifest.json
```

> The checked-in `demo_clips/*.mp4` are tiny **placeholders** so the suite runs
> anywhere; drop real footage at those paths (or edit `video_path`) for a live
> sponsor demo. Without `ANTHROPIC_API_KEY`/`ffmpeg` the suite runs transparently
> in mock mode and labels every clip accordingly.

The evaluation harness has matching soccer, hockey, and lacrosse benchmark datasets:

```bash
python -m evaluation --dataset data/eval/benchmark_soccer.json --provider mock --output soccer_report.json
python -m evaluation --dataset data/eval/benchmark_hockey.json --provider mock --output hockey_report.json
python -m evaluation --dataset data/eval/benchmark_lacrosse.json --provider mock --output lacrosse_report.json
```

## Generated Files

These are intentionally ignored by Git:

- `frontend/.next/`
- `frontend/node_modules/`
- `backend/venv/`
- `backend/uploads/`
- Python `__pycache__/`
- logs and coverage output
