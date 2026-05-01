# RefCheck AI

AI-powered sports officiating analysis demo for BorderHack. Users upload a short basketball clip, enter optional call details, and receive a verdict with rule-based reasoning.

Current stack:

- Frontend: Next.js
- Backend: FastAPI
- Analysis: ffmpeg frame extraction + four-agent Claude pipeline with mock fallback
- Optional persistence: Supabase Postgres + Supabase Storage

Supported modes:

- `AI_PROVIDER=mock` for local demos without paid keys
- `AI_PROVIDER=anthropic` with `ANTHROPIC_API_KEY` for the real four-agent pipeline

The four agents are:

1. Perception Agent: watches extracted frames and produces structured observation JSON.
2. Retrieval Agent: converts the observation into a precise rulebook query.
3. Adjudicator A: conservative reviewer that gives the original call benefit of the doubt.
4. Adjudicator B: skeptical reviewer that independently challenges the original call.

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

Keep `AI_PROVIDER=mock` for free local testing. To use the real four-agent pipeline, set:

```bash
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=your_key
```

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
4. Set `AI_PROVIDER` to `anthropic` or `mock`.
5. Add `ANTHROPIC_API_KEY` when using `anthropic`.

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
7. Retrieval Agent writes a rulebook-style query.
8. Backend retrieves the most relevant basketball rule snippets.
9. Conservative and Skeptical Adjudicator Agents independently rule on the play.
10. Backend reconciles the two adjudicators into one final verdict.
11. If AI is unavailable, the mock analyzer returns a demo-safe verdict.
12. Backend returns a verdict:
   - Fair Call
   - Bad Call
   - Inconclusive
13. Frontend displays confidence, cited rule, reasoning, perception details, and adjudicator results.

## Generated Files

These are intentionally ignored by Git:

- `frontend/.next/`
- `frontend/node_modules/`
- `backend/venv/`
- `backend/uploads/`
- Python `__pycache__/`
- logs and coverage output
