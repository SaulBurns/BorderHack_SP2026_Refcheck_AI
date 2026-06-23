"""Placeholder detectors registered but not implemented yet (Phase 5+).

They are intentionally registered so config/registry wiring can be exercised and
tested now, but invoking `detect()` raises a clear NotImplementedError instead of
silently doing nothing.
"""

from __future__ import annotations

from pathlib import Path

_PLAN = "docs/superpowers/plans/2026-06-12-sport-agnostic-perception.md"


class YOLODetector:
    """YOLOv8 object-detection eyes. Not implemented yet (planned for Phase 5)."""

    name = "yolov8"

    def detect(self, frames: list[Path], sport: str, original_call: str) -> dict:
        raise NotImplementedError(
            "YOLOv8 detector is not implemented yet (planned for Phase 5; see "
            f"{_PLAN}). Use DETECTOR=claude_vision (the default) to run perception."
        )


class HybridDetector:
    """YOLOv8 priors + Claude Vision reasoning. Not implemented yet (Phase 5)."""

    name = "hybrid"

    def detect(self, frames: list[Path], sport: str, original_call: str) -> dict:
        raise NotImplementedError(
            "Hybrid (YOLOv8 + Claude Vision) detector is not implemented yet "
            f"(planned for Phase 5; see {_PLAN}). Use DETECTOR=claude_vision "
            "(the default) to run perception."
        )
