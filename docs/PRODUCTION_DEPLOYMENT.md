# Production Deployment Guide (Sprint 15)

How to run RefCheck AI's backend in production: configuration, security,
observability, containerization, deploy, scaling, and rollback. **Nothing here is
a breaking API change** — every production feature is additive and off (or
backward compatible) by default, so an existing deployment keeps working unchanged
until you opt in.

---

## 1. What Sprint 15 adds

| Capability | Where | Default |
| --- | --- | --- |
| API-key **authentication** (write endpoints) | `services/security/auth.py` | **off** (open) until `API_KEYS` set |
| **Rate limiting** (per client, analyze endpoints) | `services/security/rate_limit.py` | **off** until `RATE_LIMIT_PER_MINUTE` > 0 |
| Structured **logging** (JSON) | `services/observability/logging_config.py` | JSON at `INFO` |
| **Metrics** (Prometheus text) | `services/observability/metrics.py` → `GET /api/metrics` | always on, additive |
| **Health / readiness** | `services/health.py` → `/api/health`, `/api/health/ready` | always on |
| **Monitoring** hooks (request-id, `X-Request-ID`) | `main.py` middleware | always on, additive |
| **Docker** multi-stage, non-root, `HEALTHCHECK` | `backend/Dockerfile` | — |

---

## 2. Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `APP_ENV` | Environment label (surfaced by health/version) | `development` |
| `APP_VERSION` | Version stamp (set to git SHA in CI) | `dev` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` | `INFO` |
| `LOG_FORMAT` | `json` (prod) or `plain` (local) | `json` |
| `RATE_LIMIT_PER_MINUTE` | Requests/min per client on `/analyze`, `/api/analyze` (`0` = disabled) | `0` |
| `API_KEYS` | Comma-separated accepted API keys (enables auth) | unset (auth off) |
| `REFCHECK_API_KEY` | Single API key (alternative to `API_KEYS`) | unset |
| `AI_PROVIDER` | `mock` / `anthropic` / `gemini` | `mock` |
| `AI_MODEL` / `GEMINI_MODEL` | Model overrides | see `services/config.py` |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | Provider secrets | unset |
| `ANTHROPIC_PROMPT_CACHE` / `GEMINI_JSON_MODE` | Opt-in provider optimizations (Sprint 14) | off |
| `FRONTEND_ORIGIN` / `CORS_ORIGINS` | Extra CORS origins (comma-separated) | built-in list + `*.vercel.app` |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_CLIPS_BUCKET` / `SUPABASE_VERDICTS_TABLE` | Optional persistence | unset (in-memory feed) |

Missing provider keys **degrade to the mock path** (surfaced in diagnostics and in
`/api/health/ready`), so the service never hard-fails on a missing secret.

---

## 3. Authentication

Off by default. To require an API key on the write endpoints (`POST /analyze`,
`POST /api/analyze`):

```bash
API_KEYS="key-a,key-b"      # or REFCHECK_API_KEY="single-key"
```

Clients then send **either** header:

```
X-API-Key: key-a
Authorization: Bearer key-a
```

Keys are compared in constant time. Read/health/media endpoints stay public.
Rejected requests get `401` and increment `refcheck_auth_failures_total`.

## 4. Rate limiting

A fixed-window, per-client (API key, else IP) limiter on the expensive analyze
endpoints. Enable with `RATE_LIMIT_PER_MINUTE` (e.g. `30`). Exceeding it returns
`429` with a `Retry-After` header and increments `refcheck_rate_limited_total`.

> **Multi-replica note:** the limiter is in-process (ideal for the free/single
> instance tier). For horizontal scaling, back `RateLimiter.allow()` with Redis —
> the callers in `main.py` don't change.

---

## 5. Observability

**Logs** — one JSON object per line (`LOG_FORMAT=json`), including `request_id`,
`method`, `path`, `status`, `duration_ms`. Ships straight into Render logs /
CloudWatch / Datadog. Use `LOG_FORMAT=plain` locally.

**Metrics** — `GET /api/metrics` returns Prometheus text-exposition format. Point a
Prometheus/Grafana/Datadog agent at it. Series:

- `refcheck_http_requests_total{method,path,status}` — path is the **route
  template** (e.g. `/api/clips/{stored_name}`), so cardinality stays bounded.
- `refcheck_http_request_duration_seconds_{count,sum}{path}`
- `refcheck_analyses_total{sport,verdict}`
- `refcheck_rate_limited_total{path}` / `refcheck_auth_failures_total{path}`

**Tracing** — every response carries `X-Request-ID` (echoed from the request or
generated), so a client id flows through the logs.

**Health**
- `GET /api/health` — liveness (fast; backward-compatible `status: "ok"` superset).
- `GET /api/health/ready` — readiness (`200` ready / `503` degraded) with per-check
  detail for provider config, `ffmpeg`, and the upload dir. Use this as the
  orchestrator readiness probe; `/api/health` as liveness.
- `GET /api/version` — version + environment.

---

## 6. Docker

Multi-stage build (`backend/Dockerfile`): a builder stage installs wheels, the
runtime stage copies only site-packages + app, runs as **non-root** (`appuser`,
uid 10001), and defines a container `HEALTHCHECK` against `/api/health`.

```bash
cd backend
docker build -t refcheck-backend .
docker run --rm -p 8000:8000 \
  -e AI_PROVIDER=anthropic -e ANTHROPIC_API_KEY=sk-ant-... \
  -e LOG_FORMAT=json -e RATE_LIMIT_PER_MINUTE=30 \
  refcheck-backend
curl -fsS localhost:8000/api/health
```

`.dockerignore` keeps the build context small (no `venv/`, `tests/`, `.env`,
generated artifacts), which also guarantees no secret is baked into the image.

---

## 7. Deploy to Render

`render.yaml` (repo root) defines the web service: `runtime: docker`,
`rootDir: backend`, `healthCheckPath: /api/health`, and the env vars above (secrets
are `sync: false`). Set `ANTHROPIC_API_KEY`, `FRONTEND_ORIGIN`, and — if enabling
auth — `API_KEYS` in the Render dashboard. Push to the tracked branch to deploy.

> Render free tier sleeps after ~15 min idle; hit `/api/health` to warm it before a
> demo. `RATE_LIMIT_PER_MINUTE=30` is a sane default for that tier.

---

## 8. Performance — before / after

The production layer is a thin middleware; it does **not** touch the analysis
pipeline. Measured offline (`scripts/prod_overhead_benchmark.py`,
`scripts/perf_benchmark.py`):

| Metric | Before | After |
| --- | --- | --- |
| Health request latency (mean) | ~1.05 ms | ~1.37 ms |
| **Middleware overhead / request** | — | **~0.32 ms (316 µs)** |
| Warm frame extraction | 0.2 ms | 0.2 ms (unchanged) |
| Pipeline orchestration (mean) | 3.77 ms | 3.77 ms (unchanged) |

~0.3 ms/request is negligible against the multi-second analyze pipeline, and the
core pipeline latency is untouched. Reproduce:

```bash
cd backend
python scripts/prod_overhead_benchmark.py --iterations 1500
python scripts/perf_benchmark.py --iterations 6 --output after.json
```

---

## 9. Production checklist

- [ ] `APP_ENV=production`, `APP_VERSION` = git SHA
- [ ] `ANTHROPIC_API_KEY` (or `GEMINI_API_KEY`) set; `/api/health/ready` returns `ready`
- [ ] `API_KEYS` set and shared with trusted clients (if auth required)
- [ ] `RATE_LIMIT_PER_MINUTE` tuned to the plan
- [ ] `FRONTEND_ORIGIN` set to the deployed frontend
- [ ] `LOG_FORMAT=json`; logs flowing to your aggregator
- [ ] Prometheus scraping `/api/metrics`
- [ ] Readiness probe → `/api/health/ready`; liveness → `/api/health`
- [ ] Container runs as non-root (built from `backend/Dockerfile`)
- [ ] Secrets provided via env / secret store, never committed
