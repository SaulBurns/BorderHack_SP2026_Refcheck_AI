# RefCheck AI — Deployment Checklist

Backend → **Render** (Docker, ffmpeg included). Frontend → **Vercel**. Optional
persistence → **Supabase**. Work top to bottom; each box is verifiable.

## 0. Pre-flight (local)

- [ ] Backend tests green: `cd backend && source venv/bin/activate && pytest tests/`
- [ ] Frontend unit tests green: `cd frontend && npm test`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Mock demo runs clean: `cd backend && python scripts/run_demo_suite.py`
- [ ] `git status` clean; changes pushed to the deploy branch

## 1. Backend on Render

- [ ] Create a Web Service (or Blueprint) from the repo; it uses `render.yaml`
      (`runtime: docker`, `rootDir: backend`, health check `/api/health`).
- [ ] Set env vars:
  - [ ] `AI_PROVIDER` = `mock` initially (switch to `anthropic`/`gemini` once healthy)
  - [ ] `ANTHROPIC_API_KEY` (if `anthropic`) **or** `GEMINI_API_KEY` (if `gemini`)
  - [ ] `AI_MODEL` (optional; default `claude-sonnet-4-5`)
  - [ ] `FRONTEND_ORIGIN` = your Vercel URL (fill in after step 2; also matches `*.vercel.app`)
- [ ] Deploy; confirm `GET /api/health` returns healthy.
- [ ] Confirm a mock `POST /api/analyze` returns a verdict + `diagnostics`.

## 2. Frontend on Vercel

- [ ] Project root directory = `frontend` (framework auto-detected as Next.js).
- [ ] Set env var **`NEXT_PUBLIC_API_BASE`** = your Render backend URL.
      ⚠️ This is read at **build time** — set it *before* deploying.
- [ ] Deploy; open the site and run one analysis end-to-end.
- [ ] Copy the Vercel URL back into Render's `FRONTEND_ORIGIN`, then redeploy the backend.

## 3. Go live with a real provider

- [ ] Flip Render `AI_PROVIDER` to `anthropic` (or `gemini`) and add the key; redeploy.
- [ ] Verify a real run: `diagnostics.provider_used == "anthropic_four_agent"` and
      `fallback_reason == null` (or use `scripts/demo_analyze.py --strict-real`).

## 4. Optional — Supabase persistence (Feed durability)

- [ ] Create a Supabase project; run `backend/supabase_schema.sql` in the SQL editor.
- [ ] Create a **public** Storage bucket named `clips`.
- [ ] On Render only (never Vercel): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
      `SUPABASE_CLIPS_BUCKET=clips`, `SUPABASE_VERDICTS_TABLE=verdicts`; redeploy.

## 5. Demo-day warm-up

- [ ] Render free tier sleeps after 15 min idle — hit `/api/health` a minute before.
- [ ] Drop real footage into `backend/demo_clips/` if showing the live pipeline.
- [ ] Have [JUDGE_CHEAT_SHEET.md](JUDGE_CHEAT_SHEET.md) and
      [DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md) open.

## Security sanity

- [ ] Service role key and provider API keys live **only** on the backend/Render.
- [ ] `NEXT_PUBLIC_*` vars are public by design — no secrets there.
- [ ] CORS is restricted to your frontend origin(s).
