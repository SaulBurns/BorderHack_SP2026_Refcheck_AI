"""Detection & tracking benchmark metrics (Sprint 18A).

Pure, dependency-free functions to score a detector's output against ground truth,
so a YOLO upgrade can be measured **before and after** on the three axes the sprint
asks for:

- **Detection accuracy** — IoU-matched precision / recall / F1 (`detection_metrics`).
- **Tracking quality** — ID switches, track fragmentation, and matched-track purity
  across a clip's frames (`tracking_metrics`).
- **Latency** — reuse `evaluation.latency.summarize_latencies`.

Both predictions and ground truth are ordinary `RawDetections` (frames of
`DetectionObject`s with a normalized center+size `bbox` and a `track_id`), so the
metrics run on the *real* detection payloads the pipeline produces — no model or
ultralytics needed to exercise them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def _xyxy(box: BoundingBox) -> tuple[float, float, float, float]:
    """Normalized center+size box -> (x1, y1, x2, y2)."""
    return (box.x - box.width / 2, box.y - box.height / 2, box.x + box.width / 2, box.y + box.height / 2)


def iou(a: BoundingBox, b: BoundingBox) -> float:
    """Intersection-over-union of two normalized boxes (0.0 when disjoint)."""
    ax1, ay1, ax2, ay2 = _xyxy(a)
    bx1, by1, bx2, by2 = _xyxy(b)
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a.width * a.height + b.width * b.height - inter
    return inter / union if union > 0 else 0.0


def match_frame(
    predicted: list[DetectionObject],
    truth: list[DetectionObject],
    iou_threshold: float = 0.5,
    match_label: bool = True,
) -> list[tuple[int, int]]:
    """Greedy IoU matching of predicted→truth objects in one frame.

    Returns (truth_index, pred_index) pairs, highest-IoU first, one-to-one. Only
    pairs with the same label (when `match_label`) and IoU ≥ threshold match.
    """
    candidates: list[tuple[float, int, int]] = []
    for t_idx, t in enumerate(truth):
        for p_idx, p in enumerate(predicted):
            if match_label and t.label != p.label:
                continue
            score = iou(t.bbox, p.bbox)
            if score >= iou_threshold:
                candidates.append((score, t_idx, p_idx))
    candidates.sort(reverse=True)
    used_truth: set[int] = set()
    used_pred: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _score, t_idx, p_idx in candidates:
        if t_idx in used_truth or p_idx in used_pred:
            continue
        used_truth.add(t_idx)
        used_pred.add(p_idx)
        matches.append((t_idx, p_idx))
    return matches


# ---------------------------------------------------------------------------
# Detection accuracy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DetectionMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float

    def to_dict(self) -> dict:
        return asdict(self)


def detection_metrics(
    predicted: RawDetections,
    truth: RawDetections,
    iou_threshold: float = 0.5,
    match_label: bool = True,
) -> DetectionMetrics:
    """Precision / recall / F1 of `predicted` vs `truth`, IoU-matched per frame."""
    tp = fp = fn = 0
    truth_by_index = {f.frame_index: f for f in truth.frames}
    pred_by_index = {f.frame_index: f for f in predicted.frames}
    for frame_index in sorted(set(truth_by_index) | set(pred_by_index)):
        t_objs = truth_by_index.get(frame_index, FrameDetections(frame_index=frame_index, objects=[])).objects
        p_objs = pred_by_index.get(frame_index, FrameDetections(frame_index=frame_index, objects=[])).objects
        matches = match_frame(p_objs, t_objs, iou_threshold, match_label)
        tp += len(matches)
        fp += len(p_objs) - len(matches)
        fn += len(t_objs) - len(matches)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return DetectionMetrics(
        true_positives=tp, false_positives=fp, false_negatives=fn,
        precision=round(precision, 4), recall=round(recall, 4), f1=round(f1, 4),
    )


# ---------------------------------------------------------------------------
# Tracking quality
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrackingMetrics:
    gt_tracks: int            # distinct ground-truth track_ids
    pred_tracks: int          # distinct predicted track_ids
    id_switches: int          # times a GT track's matched pred id changed frame-to-frame
    track_purity: float       # avg fraction of a GT track covered by its dominant pred id
    matched_ratio: float      # fraction of GT (track, frame) observations that got a match

    def to_dict(self) -> dict:
        return asdict(self)


def tracking_metrics(
    predicted: RawDetections,
    truth: RawDetections,
    iou_threshold: float = 0.5,
) -> TrackingMetrics:
    """Tracking quality: ID switches, per-track purity, matched-observation ratio.

    For each frame, GT objects are IoU-matched to predictions; the matched
    prediction's `track_id` is attributed to the GT object's `track_id`. Following
    each GT track across frames, an **ID switch** is a change in the attributed pred
    id, and **purity** is how consistently one pred id covers the GT track — the two
    core signals of tracking stability across a clip.
    """
    truth_by_index = {f.frame_index: f for f in truth.frames}
    pred_by_index = {f.frame_index: f for f in predicted.frames}
    # gt_track_id -> ordered list of attributed pred track_ids (None = no match this frame)
    sequences: dict[int, list[int | None]] = {}
    gt_track_ids: set[int] = set()
    pred_track_ids: set[int] = set()
    total_obs = matched_obs = 0

    for frame_index in sorted(set(truth_by_index) | set(pred_by_index)):
        t_objs = truth_by_index.get(frame_index, FrameDetections(frame_index=frame_index, objects=[])).objects
        p_objs = pred_by_index.get(frame_index, FrameDetections(frame_index=frame_index, objects=[])).objects
        for p in p_objs:
            if p.track_id is not None:
                pred_track_ids.add(p.track_id)
        matches = dict(match_frame(p_objs, t_objs, iou_threshold))  # truth_idx -> pred_idx
        for t_idx, t in enumerate(t_objs):
            if t.track_id is None:
                continue
            gt_track_ids.add(t.track_id)
            total_obs += 1
            pred_obj = p_objs[matches[t_idx]] if t_idx in matches else None
            if pred_obj is not None:
                matched_obs += 1
            sequences.setdefault(t.track_id, []).append(pred_obj.track_id if pred_obj else None)

    id_switches = 0
    purities: list[float] = []
    for seq in sequences.values():
        assigned = [pid for pid in seq if pid is not None]
        if not assigned:
            continue
        prev = None
        for pid in assigned:
            if prev is not None and pid != prev:
                id_switches += 1
            prev = pid
        dominant = max(set(assigned), key=assigned.count)
        purities.append(assigned.count(dominant) / len(assigned))

    return TrackingMetrics(
        gt_tracks=len(gt_track_ids),
        pred_tracks=len(pred_track_ids),
        id_switches=id_switches,
        track_purity=round(sum(purities) / len(purities), 4) if purities else 0.0,
        matched_ratio=round(matched_obs / total_obs, 4) if total_obs else 0.0,
    )
