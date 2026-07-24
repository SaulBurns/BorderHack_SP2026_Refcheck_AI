"""YOLO detector benchmark — before/after the Sprint 18A upgrade.

Measures the three axes the sprint asks for on the *real* detection code paths:

- **Detection accuracy** — IoU precision / recall / F1 vs ground truth.
- **Tracking quality** — ID switches, track purity, matched-observation ratio.
- **Latency** — wall-clock of `YoloInferenceService.infer()` over the clip's frames.

Two modes:

- **`--live`** — the genuine before/after. Runs the real Ultralytics pipeline on a
  frames directory for two model configs (`--before yolov8n.pt --after yolo26n.pt`)
  and, if a `--truth` ground-truth JSON is given, scores detection + tracking for
  each. Requires `ultralytics` installed and real footage — the honest source of a
  model-vs-model delta.

- **offline (default)** — a harness self-check on a bundled synthetic labeled clip:
  scores detection + tracking for one deterministic predictor and times the real
  `infer()` orchestration (simulated per-frame latency). This validates the metrics
  and the upgraded config end-to-end without a model; it does **not** fabricate a
  yolov8-vs-yolo26 accuracy delta — run `--live` for that.

Usage:
    python scripts/yolo_benchmark.py                      # offline self-check report
    python scripts/yolo_benchmark.py --live \
        --frames /path/to/frames --truth truth.json \
        --before yolov8n.pt --after yolo26n.pt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import config
from services.detectors.benchmark import detection_metrics, tracking_metrics
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)
from services.detectors.yolo_inference import DETECTOR_VERSION, YoloInferenceService, RawBox


# ---------------------------------------------------------------------------
# Synthetic labeled clip (offline self-check)
# ---------------------------------------------------------------------------

def _obj(label, x, y, track_id):
    return DetectionObject(label=label, confidence=0.9,
                           bbox=BoundingBox(x=x, y=y, width=0.1, height=0.2), track_id=track_id)


def _synthetic_truth(frames: int = 8) -> RawDetections:
    """A ground-truth clip: a player (track 1) and a ball (track 2) crossing frame."""
    out = []
    for i in range(frames):
        x = 0.2 + 0.6 * i / (frames - 1)
        out.append(FrameDetections(frame_index=i, objects=[
            _obj("person", x, 0.5, track_id=1),
            _obj("sports ball", x + 0.05, 0.45, track_id=2),
        ]))
    return RawDetections(model="ground_truth", detector_version="gt", frames=out)


def _synthetic_prediction(truth: RawDetections) -> RawDetections:
    """A plausible detector output: tracks the player cleanly, drops the ball on one
    frame and switches its track id once — so detection/tracking metrics are non-trivial."""
    frames = []
    for f in truth.frames:
        objs = []
        for o in f.objects:
            if o.label == "sports ball" and f.frame_index == 3:
                continue  # dropped detection (a miss)
            pred_track = {1: 10, 2: 20 if f.frame_index < 5 else 21}[o.track_id]  # ball id switch @5
            objs.append(DetectionObject(label=o.label, confidence=0.8, bbox=o.bbox, track_id=pred_track))
        frames.append(FrameDetections(frame_index=f.frame_index, objects=objs))
    return RawDetections(model=config.resolved_yolo_model(), detector_version=DETECTOR_VERSION, frames=frames)


def _measure_infer_latency(frame_count: int, per_frame_seconds: float = 0.02) -> dict:
    """Time the real infer() orchestration with a simulated-latency predictor."""
    def predictor(_path):
        time.sleep(per_frame_seconds)
        return [RawBox("person", 0.9, 10, 10, 30, 60, 100, 200, track_id=1)]

    service = YoloInferenceService(predictor=predictor)
    frames = [Path(f"f{i}.jpg") for i in range(frame_count)]
    started = time.perf_counter()
    service.infer(frames)
    total_ms = (time.perf_counter() - started) * 1000
    return {"frames": frame_count, "total_ms": round(total_ms, 2),
            "per_frame_ms": round(total_ms / frame_count, 2) if frame_count else 0.0}


# ---------------------------------------------------------------------------
# Live model runs
# ---------------------------------------------------------------------------

def _load_truth(path: str) -> RawDetections:
    return RawDetections(**json.loads(Path(path).read_text()))


def _run_live_model(model: str, frames_dir: str) -> tuple[RawDetections, float]:
    frames = sorted(Path(frames_dir).glob("*.jpg"))
    service = YoloInferenceService(model=model)
    # Warm up: the first inference pays a one-time torch + weights load. Excluding it
    # makes the before/after latency a fair steady-state comparison (the timed pass
    # re-runs from frame 0 with persist=False, so tracking is unaffected).
    if frames:
        service.infer(frames[:1])
    started = time.perf_counter()
    detections = service.infer(frames)
    return detections, (time.perf_counter() - started) * 1000


def _score(label: str, detections: RawDetections, truth: RawDetections | None, latency_ms: float) -> dict:
    row: dict = {"config": label, "model": detections.model, "latency_ms": round(latency_ms, 2)}
    if truth is not None:
        row["detection"] = detection_metrics(detections, truth).to_dict()
        row["tracking"] = tracking_metrics(detections, truth).to_dict()
    return row


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _render_markdown(mode: str, rows: list[dict], note: str) -> str:
    lines = [
        "# YOLO detector benchmark (Sprint 18A)",
        "",
        f"- Mode: `{mode}`  ·  Detector version: `{DETECTOR_VERSION}`  ·  "
        f"Default weights: `{config.resolved_yolo_model()}`",
        "",
        "| Config | Model | Precision | Recall | F1 | ID switches | Track purity | Matched | Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        det = r.get("detection", {})
        trk = r.get("tracking", {})
        lines.append(
            f"| {r['config']} | `{r['model']}` | "
            f"{det.get('precision', '—')} | {det.get('recall', '—')} | {det.get('f1', '—')} | "
            f"{trk.get('id_switches', '—')} | {trk.get('track_purity', '—')} | "
            f"{trk.get('matched_ratio', '—')} | {r['latency_ms']} |"
        )
    lines += ["", note, ""]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="yolo_benchmark", description=__doc__)
    p.add_argument("--live", action="store_true", help="Run real Ultralytics models (needs ultralytics + footage).")
    p.add_argument("--frames", default=None, help="Frames directory (*.jpg) for --live.")
    p.add_argument("--truth", default=None, help="Ground-truth RawDetections JSON (optional; enables accuracy).")
    p.add_argument("--before", default="yolov8n.pt", help="Baseline model for --live (default: yolov8n.pt).")
    p.add_argument("--after", default=config.DEFAULT_YOLO_MODEL, help="Upgraded model for --live.")
    p.add_argument("--md", default="evaluation/reports/yolo_benchmark.md", help="Markdown report path.")
    p.add_argument("--json", dest="json_out", default="evaluation/reports/yolo_benchmark.json", help="JSON path.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    truth = _load_truth(args.truth) if args.truth else None

    if args.live:
        if not args.frames:
            print("error: --live requires --frames <dir>", file=sys.stderr)
            return 2
        rows = []
        for label, model in (("before", args.before), ("after", args.after)):
            detections, latency_ms = _run_live_model(model, args.frames)
            rows.append(_score(label, detections, truth, latency_ms))
        note = (
            "_Live before/after over real footage (warm-model latency; one-time torch + "
            "weights load excluded)._" if truth
            else "_Live run without `--truth`: **latency only** — warm-model steady-state "
            "(one-time torch + weights load excluded); add `--truth <RawDetections JSON>` "
            "over labeled footage for detection accuracy + tracking quality._"
        )
        mode = "live"
    else:
        synthetic_truth = _synthetic_truth()
        prediction = _synthetic_prediction(synthetic_truth)
        latency = _measure_infer_latency(frame_count=10)
        rows = [_score("current (offline self-check)", prediction, synthetic_truth, latency["total_ms"])]
        note = (
            "_Offline harness self-check on a synthetic labeled clip — it validates the "
            "detection/tracking metrics and the upgraded config, but is **not** a "
            "yolov8-vs-yolo26 comparison. Run `--live --frames <dir> --truth <json> "
            "--before yolov8n.pt --after yolo26n.pt` (with `ultralytics` installed and "
            "labeled footage) for the real before/after deltas._"
        )
        mode = "offline"

    payload = {"mode": mode, "detector_version": DETECTOR_VERSION,
               "default_model": config.resolved_yolo_model(), "results": rows}
    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(json.dumps(payload, indent=2))
    Path(args.md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md).write_text(_render_markdown(mode, rows, note))

    print(f"[{mode}] YOLO benchmark — detector v{DETECTOR_VERSION}, default {config.resolved_yolo_model()}")
    for r in rows:
        det = r.get("detection", {})
        print(f"  {r['config']:>28} | model={r['model']} f1={det.get('f1','—')} "
              f"id_switches={r.get('tracking',{}).get('id_switches','—')} latency_ms={r['latency_ms']}")
    print(f"Wrote {args.md} and {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
