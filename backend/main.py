from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.frontend_adapter import to_frontend_response
from services.mock_analyzer import analyze_clip
from services.video_processor import save_uploaded_clip

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
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
    mock_result = analyze_clip(
        file=file,
        sport=sport,
        level_of_play=level,
        league=league,
        original_call=original_call,
        referee_name=ref_name,
        video_metadata=video_metadata,
    )
    return to_frontend_response(mock_result)
