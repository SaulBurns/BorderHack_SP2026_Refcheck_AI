"""Frame extraction from uploaded clips (Sprint 7 extraction).

ffprobe measures duration; ffmpeg samples evenly-spaced JPEG frames. A
clip_id-keyed on-disk cache (Sprint 6) skips both subprocesses on re-analysis.
Extracted out of ai_analyzer verbatim; behavior is unchanged."""

from __future__ import annotations

import subprocess
from pathlib import Path

FRAME_DIR = Path(__file__).resolve().parents[2] / "uploads" / "frames"


def _video_duration_seconds(video_path: Path) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None

    return duration if duration > 0 else None


def _extract_frames(video_path: str | None, clip_id: str, max_frames: int = 10) -> list[Path]:
    if not video_path:
        return []

    source = Path(video_path)
    if not source.exists():
        return []

    output_dir = FRAME_DIR / clip_id

    # Frame cache (Sprint 6 perf): clip_id is derived from the stored path + byte
    # size, so identical frames for a given clip already on disk are byte-for-byte
    # reusable. Re-analysis of the same clip (demo suite, benchmark loops, a user
    # resubmitting) then skips both the ffprobe duration probe and the ffmpeg
    # decode — the two subprocesses that dominate warm-path latency. Cold path is
    # unchanged; the extracted frames are identical either way.
    cached = sorted(output_dir.glob("frame_*.jpg"))[:max_frames]
    if cached:
        return cached

    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%03d.jpg")

    duration = _video_duration_seconds(source)
    fps = 1 if not duration else max_frames / duration

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        f"fps={fps:.4f},scale=768:-1",
        "-frames:v",
        str(max_frames),
        output_pattern,
    ]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=45,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    return sorted(output_dir.glob("frame_*.jpg"))[:max_frames]
