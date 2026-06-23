"""Detector abstraction (Phase 4 of the sport-agnostic perception plan).

A `Detector` is the "eyes" of the pipeline: it turns extracted frames into a
perception payload. The default `ClaudeVisionDetector` wraps the existing
perception logic so behavior is unchanged; YOLOv8/hybrid detectors are
placeholders for later phases.

In this phase `detect()` returns the raw perception dict (the contract the rest
of the pipeline already consumes). Mapping to the typed `PerceptionCore` model
is intentionally deferred to a later phase to avoid any response-shape change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Detector(Protocol):
    """Protocol every detector implementation must satisfy.

    Attributes:
        name: Stable identifier used by the registry/config (e.g. "claude_vision").
    """

    name: str

    def detect(self, frames: list[Path], sport: str, original_call: str) -> dict:
        """Produce a perception payload for the given frames.

        Args:
            frames: Ordered list of extracted frame image paths.
            sport: Normalized sport key (e.g. "basketball").
            original_call: The on-court call text, or "" if none.

        Returns:
            The perception dict consumed by the downstream pipeline.
        """
        ...
