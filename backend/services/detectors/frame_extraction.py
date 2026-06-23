"""Frame extraction pipeline for the detector layer (Phase 5).

Video -> frame image files is handled upstream (ai_analyzer._extract_frames via
ffmpeg). This module is the detector-side intake: it validates already-extracted
frame paths and assigns stable frame indices for inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ExtractedFrame:
    """An extracted frame ready for inference."""

    index: int
    path: Path


def prepare_frames(frame_paths: Iterable[str | Path]) -> list[ExtractedFrame]:
    """Validate and index extracted frame files.

    Non-existent paths are skipped (a detector should never fail because one
    frame failed to extract). Indices are assigned contiguously over the frames
    that survive, preserving input order.
    """
    prepared: list[ExtractedFrame] = []
    for raw_path in frame_paths:
        path = Path(raw_path)
        if path.exists() and path.is_file():
            prepared.append(ExtractedFrame(index=len(prepared), path=path))
    return prepared
