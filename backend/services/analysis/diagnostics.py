"""Diagnostics payload builders (Sprint 7 extraction).

Additive diagnostics: detection counts and YOLO-influence flags exposed for
evaluation/debugging. Never affects the verdict. Unchanged."""

from __future__ import annotations

from services.detectors import RawDetections
from services.perception_schema import SCHEMA_VERSION


_PERSON_LABELS = {"person", "player"}
_BALL_LABELS = {"sports ball", "basketball", "ball"}


def _detection_summary(detections: RawDetections | None) -> dict:
    """Compact, label-based counts for diagnostics (no heavy new work)."""
    if detections is None:
        return {
            "detection_frame_count": 0,
            "detection_object_count": 0,
            "tracking_present": False,
            "tracked_object_count": 0,
            "player_count": 0,
            "ball_present": False,
        }
    object_count = 0
    tracked = 0
    players: set = set()
    ball_present = False
    for frame in detections.frames:
        for obj in frame.objects:
            object_count += 1
            label = obj.label.lower()
            if obj.track_id is not None:
                tracked += 1
            if label in _PERSON_LABELS:
                players.add(obj.track_id if obj.track_id is not None else f"anon-{object_count}")
            if label in _BALL_LABELS:
                ball_present = True
    return {
        "detection_frame_count": len(detections.frames),
        "detection_object_count": object_count,
        "tracking_present": tracked > 0,
        "tracked_object_count": tracked,
        "player_count": len(players),
        "ball_present": ball_present,
    }


def _yolo_influence(detections: RawDetections | None, tracked_evidence: dict | None) -> dict:
    """Diagnostics that make it obvious *when and how* YOLO shaped the verdict.

    Reuses the already-computed `tracked_evidence` (no recomputation). `yolo_influenced`
    is True whenever detections were available to feed adjudication; the remaining
    flags show which specific signals (possession, defender, ball trajectory,
    confidence calibration) actually reached the adjudicators/reconciliation.
    """
    evidence = tracked_evidence if isinstance(tracked_evidence, dict) else {}
    tracking_confidence = evidence.get("tracking_confidence")
    return {
        "yolo_influenced": detections is not None,
        "tracked_evidence_present": bool(evidence),
        "tracking_confidence": tracking_confidence,
        "possession_summary": evidence.get("possession_summary"),
        "defender_tracked": evidence.get("defender_track_id") is not None,
        "ball_trajectory_present": evidence.get("ball_movement") is not None,
        # Reconciliation only nudges confidence when a tracking-confidence signal
        # was available (see _reconcile / _build_response).
        "influenced_reconciliation": tracking_confidence is not None,
    }


def _diagnostics_payload(
    provider_used: str,
    detections: RawDetections | None,
    detector: str | None = None,
    frames_analyzed: int = 0,
    fallback_reason: str | None = None,
    tracked_evidence: dict | None = None,
) -> dict:
    """Additive diagnostics block to support evaluation and debugging (Phase 9/10B).

    Makes it obvious what actually ran: which detector path, whether detections
    (and stable track_ids) were produced, whether sport_details were enriched
    from detections or came purely from perception, compact debug counts, and
    (Sprint 2) whether/how YOLO tracking influenced the decision.
    Metadata status is attached later in analyze_clip once game_context resolves.
    """
    detector_path = detector or ("mock" if provider_used == "mock" else "unknown")
    summary = _detection_summary(detections)
    return {
        "schema_version": SCHEMA_VERSION,
        "provider_used": provider_used,
        "detector": detector_path,
        # None on a real anthropic run; the reason string when the pipeline
        # degraded to mock (missing key/ffmpeg/ultralytics, or AI_PROVIDER=mock).
        "fallback_reason": fallback_reason,
        "frames_analyzed": frames_analyzed,
        "detections_present": detections is not None,
        "sport_details_source": "detections" if detections is not None else "perception",
        # metadata_* are filled in by analyze_clip (after game_context resolves).
        "metadata_attempted": False,
        "metadata_status": "not_applicable",
        **summary,
        **_yolo_influence(detections, tracked_evidence),
    }
