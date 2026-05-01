from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "RefCheck AI backend is running"}

@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    return {
        "verdict": "Inconclusive",
        "confidence": "Low",
        "call_type": "Block / Charge",
        "reasoning": "The backend received the clip successfully. AI analysis will be added next.",
        "rule_applied": "Legal guarding position",
        "evidence": [
            "Video uploaded successfully",
            "Frame extraction not added yet",
            "AI analysis pending"
        ]
    }