# RefCheck AI — Troubleshooting

Most problems fall into: **backend not running**, **ffmpeg missing**, **provider/key
misconfig**, or **frontend can't reach backend**. RefCheck degrades gracefully by
design, so check the `diagnostics` block first — it usually tells you exactly what
happened.

## Read the diagnostics first

Every `/api/analyze` response includes a `diagnostics` block:

```json
"diagnostics": {
  "provider_used": "mock",
  "detector": "claude_vision",
  "fallback_reason": "ANTHROPIC_API_KEY is not set",
  "frames_analyzed": 0,
  "detections_present": false,
  "yolo_influenced": false,
  "metadata_status": "skipped"
}
```

- `provider_used: "mock"` + a `fallback_reason` → the real pipeline **did not** run;
  the reason string says why (missing key, missing ffmpeg, `AI_PROVIDER=mock`, …).
- `provider_used: "anthropic_four_agent"` and `fallback_reason: null` → the real
  four-agent pipeline ran.

The `scripts/demo_analyze.py` CLI prints this decisively (`REAL PIPELINE RAN: YES/NO`)
and has a `--strict-real` mode that exits nonzero instead of silently degrading.

## Backend

| Symptom | Cause | Fix |
|---|---|---|
| `Address already in use` on :8000 | Port taken | `lsof -i :8000` then `kill -9 <PID>`; or `--port 8001` |
| Every verdict is `inconclusive`, `provider_used: mock` | `AI_PROVIDER=mock` (default) | Set `AI_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` for the real pipeline |
| `fallback_reason: "...ffmpeg..."` / `frames_analyzed: 0` | ffmpeg not installed | `brew install ffmpeg` (macOS) / `apt-get install ffmpeg`; the Docker image already includes it |
| `fallback_reason: "ANTHROPIC_API_KEY is not set"` | Key missing/typo | Export the key in the backend env (not the frontend) |
| `AI_PROVIDER=gemini` fails | `google-genai` not installed | `pip install google-genai` and set `GEMINI_API_KEY` |
| Unsupported `AI_PROVIDER` value → error at request time | Typo (e.g. `openai`) | Use `mock`, `anthropic`, or `gemini` — invalid values fail loudly on purpose |
| YOLO / hybrid detector errors | `ultralytics` missing | Hybrid degrades to Claude-only automatically (`detections_present: false`); install `ultralytics` for tracking |
| `game_context` is `unresolved` / `unavailable` | No date/team hints, or `nba_api` missing/rate-limited | Optional & guarded — never blocks a verdict. Add a date/teams to the filename or pass demo hints |
| Import errors from `rules.*` | Process started outside `backend/` | Start the server from the `backend/` directory |

Quick backend sanity check (no venv needed):

```bash
cd backend && python3 -m compileall services/ main.py
```

Run the tests:

```bash
cd backend && source venv/bin/activate && pytest tests/
```

## Frontend

| Symptom | Cause | Fix |
|---|---|---|
| "Can't reach the analysis server" | Backend down or wrong base URL | Start the backend; set `NEXT_PUBLIC_API_BASE` in `frontend/.env.local` |
| Verdict page says "No verdict found" | `sessionStorage` was cleared / opened directly | Re-run an analysis; verdicts are cached per session by `clip_id` |
| Clip won't play on the Verdict screen | Backend clip URL unreachable / not persisted | Falls back to the locally cached upload; ensure the backend `clip_url` is reachable, or use Supabase for durable clips |
| Feed is empty | Backend down or no persistence | Expected — the Feed falls back to demo clips and never throws |
| Stale styles / blank page after an update | Cached `.next` build | `rm -rf frontend/.next && npm run dev`, then hard refresh (Cmd+Shift+R) |
| `NEXT_PUBLIC_API_BASE` change not taking effect on Vercel | It's read at **build time** | Redeploy after changing it |

Build check:

```bash
cd frontend && npm run build     # verifies the app compiles
cd frontend && npm test          # overlay + sport-evidence unit tests
```

## Deployment (Render + Vercel)

| Symptom | Fix |
|---|---|
| Render backend cold and slow | Free tier sleeps after 15 min — hit `/api/health` to warm it up before a demo |
| CORS errors in the browser | Set `FRONTEND_ORIGIN` (or `CORS_ORIGINS`) on the backend to your exact Vercel URL |
| Frontend calls `localhost` in production | `NEXT_PUBLIC_API_BASE` wasn't set at build time on Vercel — set it and redeploy |
| Videos don't persist across the Feed | Configure Supabase (`SUPABASE_URL` + service role key on the backend only) and make the `clips` bucket public |

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for the full go-live sequence.
