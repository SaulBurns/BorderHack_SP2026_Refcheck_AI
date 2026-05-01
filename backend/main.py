import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from services.ai_analyzer import analyze_clip
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

app = FastAPI()

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    allowed_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "RefCheck AI backend is running"}

@app.get("/api/health")
def api_health():
    return {"status": "ok", "message": "RefCheck AI backend is running"}

@app.get("/api/clips/{stored_name}")
def get_uploaded_clip(stored_name: str):
    safe_name = Path(stored_name).name
    clip_path = UPLOAD_DIR / safe_name

    if not clip_path.exists() or not clip_path.is_file():
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(clip_path)

@app.post("/analyze")
async def analyze_video(
    file: UploadFile = File(...),
    sport: str = Form("Basketball"),
    level_of_play: str | None = Form(None),
    league: str | None = Form(None),
    original_call: str | None = Form(None),
    referee_name: str | None = Form(None),
):
    video_metadata = await save_uploaded_clip(file)

    return analyze_clip(
        file=file,
        sport=sport,
        level_of_play=level_of_play,
        league=league,
        original_call=original_call,
        referee_name=referee_name,
        video_metadata=video_metadata,
    )

@app.post("/api/analyze")
async def analyze_video_for_frontend(
    file: UploadFile = File(...),
    sport: str = Form("basketball"),
    level: str | None = Form(None),
    league: str | None = Form(None),
    original_call: str | None = Form(None),
    ref_name: str | None = Form(None),
):
    video_metadata = await save_uploaded_clip(file)
    return analyze_clip(
        file=file,
        sport=sport,
        level_of_play=level,
        league=league,
        original_call=original_call,
        referee_name=ref_name,
        video_metadata=video_metadata,
    )
