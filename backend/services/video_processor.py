from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"


def _safe_filename(filename: str | None) -> str:
    if not filename:
        return "clip.mp4"
    return Path(filename).name.replace(" ", "_")


async def save_uploaded_clip(file: UploadFile) -> dict:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(file.filename)
    stored_name = f"{uuid4().hex}_{safe_name}"
    stored_path = UPLOAD_DIR / stored_name

    size_bytes = 0
    with stored_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size_bytes += len(chunk)
            output.write(chunk)

    await file.seek(0)

    return {
        "filename": file.filename or safe_name,
        "content_type": file.content_type or "unknown",
        "size_bytes": size_bytes,
        "stored_path": str(stored_path),
    }
