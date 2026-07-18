import asyncio
import logging
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from services import health
from services.ai_analyzer import FRAME_DIR, analyze_clip
from services.observability import configure_logging, metrics
from services.security import RateLimiter, api_key_auth, rate_limit_per_minute
from services.supabase_store import list_feed, persist_analysis
from services.video_processor import UPLOAD_DIR, save_uploaded_clip


def _load_local_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path) as env_file:
        for line in env_file:
            value = line.strip()
            if not value or value.startswith("#") or "=" not in value:
                continue
            key, raw = value.split("=", 1)
            os.environ.setdefault(key.strip(), raw.strip().strip('"').strip("'"))


if load_dotenv:
    load_dotenv()
else:
    _load_local_env()

# Structured logging must be configured before the first log line (Sprint 15).
configure_logging()
logger = logging.getLogger("refcheck")

app = FastAPI(title="RefCheck AI", version=health.app_version())

# Endpoints protected by rate limiting (the expensive write paths). Reads the raw
# request path, so both `/analyze` and `/api/analyze` are covered.
_RATE_LIMITED_PATHS = frozenset({"/analyze", "/api/analyze"})
# Shared limiter; its limit is refreshed per-request from the env so operators can
# tune it without a redeploy and tests can exercise it deterministically.
_rate_limiter = RateLimiter(limit=0)

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
    "https://border-hack-sp-2026-refcheck-ai.vercel.app",
]
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    allowed_origins.extend(
        origin.strip()
        for origin in frontend_origin.split(",")
        if origin.strip()
    )
cors_origins = os.getenv("CORS_ORIGINS")
if cors_origins:
    allowed_origins.extend(
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(allowed_origins)),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client_key(request: Request) -> str:
    """Rate-limit bucket: the API key when present, else the client IP."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{api_key}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def _route_label(request: Request) -> str:
    """Route template (bounded cardinality) for metrics, e.g. /api/clips/{name}."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Request-id propagation + structured request log + metrics + rate limiting.

    All additive: it never alters a response body, only adds an `X-Request-ID`
    header and records telemetry. Rate limiting engages only when
    `RATE_LIMIT_PER_MINUTE` is set (>0).
    """
    request_id = request.headers.get("x-request-id") or uuid4().hex[:16]
    start = perf_counter()

    limit = rate_limit_per_minute()
    if limit > 0 and request.method == "POST" and request.url.path in _RATE_LIMITED_PATHS:
        _rate_limiter.limit = limit
        allowed, retry_after = _rate_limiter.allow(_client_key(request))
        if not allowed:
            metrics.inc("refcheck_rate_limited_total", {"path": request.url.path})
            logger.warning(
                "rate limited",
                extra={"request_id": request_id, "path": request.url.path},
            )
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please retry later."},
                status_code=429,
                headers={"Retry-After": str(int(retry_after) + 1), "X-Request-ID": request_id},
            )

    try:
        response = await call_next(request)
    except Exception:
        duration = perf_counter() - start
        label = _route_label(request)
        metrics.inc(
            "refcheck_http_requests_total",
            {"method": request.method, "path": label, "status": "500"},
        )
        metrics.observe("refcheck_http_request_duration_seconds", duration, {"path": label})
        logger.exception(
            "request failed",
            extra={"request_id": request_id, "method": request.method, "path": label},
        )
        raise

    duration = perf_counter() - start
    label = _route_label(request)
    response.headers["X-Request-ID"] = request_id
    metrics.inc(
        "refcheck_http_requests_total",
        {"method": request.method, "path": label, "status": str(response.status_code)},
    )
    metrics.observe("refcheck_http_request_duration_seconds", duration, {"path": label})
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": label,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        },
    )
    return response


def _record_analysis(result: dict, sport: str) -> None:
    """Count a completed analysis by sport + final verdict (best-effort)."""
    try:
        verdict = (result or {}).get("verdict", {}).get("verdict", "unknown")
    except AttributeError:
        verdict = "unknown"
    metrics.inc("refcheck_analyses_total", {"sport": sport, "verdict": str(verdict)})


# --- Liveness / readiness / observability -----------------------------------

@app.get("/")
def home():
    return {"message": "RefCheck AI backend is running"}


@app.get("/api/health")
def api_health():
    """Liveness — backward-compatible superset (still returns status/message)."""
    return health.liveness()


@app.get("/api/health/ready")
def api_ready():
    """Readiness — provider/ffmpeg/upload-dir checks. 503 when degraded."""
    report = health.readiness()
    status_code = 200 if report["status"] == "ready" else 503
    return JSONResponse(report, status_code=status_code)


@app.get("/api/version")
def api_version():
    return {"version": health.app_version(), "environment": health.app_environment()}


@app.get("/api/metrics")
def api_metrics():
    """Prometheus text-exposition metrics for scraping."""
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


# --- Media -------------------------------------------------------------------

@app.get("/api/clips/{stored_name}")
def get_uploaded_clip(stored_name: str):
    safe_name = Path(stored_name).name
    clip_path = UPLOAD_DIR / safe_name

    if not clip_path.exists() or not clip_path.is_file():
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(clip_path)


@app.get("/api/frames/{clip_id}/{frame_name}")
def get_analysis_frame(clip_id: str, frame_name: str):
    safe_clip_id = Path(clip_id).name
    safe_frame_name = Path(frame_name).name
    frame_path = FRAME_DIR / safe_clip_id / safe_frame_name

    if not frame_path.exists() or not frame_path.is_file():
        raise HTTPException(status_code=404, detail="Analysis frame not found")

    return FileResponse(frame_path, media_type="image/jpeg")


@app.get("/api/feed")
def api_feed(limit: int = 20):
    return {"items": list_feed(limit=limit)}


# --- Analysis (write endpoints — optional auth) ------------------------------

@app.post("/analyze", dependencies=[Depends(api_key_auth)])
async def analyze_video(
    file: UploadFile = File(...),
    sport: str = Form("Basketball"),
    level_of_play: str | None = Form(None),
    league: str | None = Form(None),
    original_call: str | None = Form(None),
    referee_name: str | None = Form(None),
):
    video_metadata = await save_uploaded_clip(file)
    # analyze_clip is a blocking, multi-second CPU+network pipeline. Run it in a
    # worker thread so it does not stall the event loop and block other requests
    # (Sprint 6 perf). The returned response is identical.
    result = await asyncio.to_thread(
        analyze_clip,
        file=file,
        sport=sport,
        level_of_play=level_of_play,
        league=league,
        original_call=original_call,
        referee_name=referee_name,
        video_metadata=video_metadata,
    )
    response = persist_analysis(
        result=result,
        video_metadata=video_metadata,
        sport=sport,
        level_of_play=level_of_play or "",
        league=league or "",
        original_call=original_call or "",
        referee_name=referee_name or "",
    )
    _record_analysis(response, sport)
    return response


@app.post("/api/analyze", dependencies=[Depends(api_key_auth)])
async def analyze_video_for_frontend(
    file: UploadFile = File(...),
    sport: str = Form("basketball"),
    level: str | None = Form(None),
    league: str | None = Form(None),
    original_call: str | None = Form(None),
    ref_name: str | None = Form(None),
):
    # NB: avoid reserved LogRecord attribute names (e.g. `filename`) in `extra`.
    logger.info(
        "analyze received",
        extra={"sport": sport, "clip_filename": file.filename},
    )
    video_metadata = await save_uploaded_clip(file)
    # Offload the blocking pipeline to a worker thread (Sprint 6 perf); identical
    # response, but the event loop stays free to serve concurrent requests.
    result = await asyncio.to_thread(
        analyze_clip,
        file=file,
        sport=sport,
        level_of_play=level,
        league=league,
        original_call=original_call,
        referee_name=ref_name,
        video_metadata=video_metadata,
    )
    response = persist_analysis(
        result=result,
        video_metadata=video_metadata,
        sport=sport,
        level_of_play=level or "",
        league=league or "",
        original_call=original_call or "",
        referee_name=ref_name or "",
    )
    _record_analysis(response, sport)
    return response
