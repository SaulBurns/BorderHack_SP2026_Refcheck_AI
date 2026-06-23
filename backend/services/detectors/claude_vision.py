"""Claude Vision detector — the default, behavior-preserving implementation.

It delegates verbatim to the existing `_perception_agent` so the perception flow
is byte-for-byte identical to the pre-Phase-4 pipeline.
"""

from __future__ import annotations

from pathlib import Path

from services.detectors.detection_models import DetectorResult


class ClaudeVisionDetector:
    """Wraps the current Claude Vision perception logic (no behavior change)."""

    name = "claude_vision"

    def detect(self, frames: list[Path], sport: str, original_call: str) -> DetectorResult:
        # Imported lazily to avoid a circular import (ai_analyzer imports the
        # detector registry). At call time ai_analyzer is fully initialized.
        from services.ai_analyzer import _perception_agent

        perception = _perception_agent(frames, original_call, sport)
        # Pass the perception dict through unchanged (no detections for pure vision).
        return DetectorResult(perception=perception, detections=None)
