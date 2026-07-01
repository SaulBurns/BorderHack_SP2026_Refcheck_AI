"""Evaluation runner CLI — completes the Phase 9 evaluation framework.

Runs the live analysis pipeline over a labeled dataset and produces an
EvaluationReport (accuracy, confusion matrix, per-class precision/recall/F1,
Cohen's kappa, confidence calibration) as JSON.

Usage:
    python -m evaluation --dataset data/eval/labeled_clips.json \\
        --output report.json --provider anthropic --detector hybrid

The dataset is a JSON array; each row needs `clip_id`, `sport`,
`ground_truth_verdict`, and optionally `video_path` and `original_call` (used to
drive the pipeline). Mock provider runs fully offline (no video/key required).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from evaluation.models import Prediction, prediction_from_response
from evaluation.runner import EvaluationReport, evaluate_predictions, load_labeled_clips

PROVIDERS = ("anthropic", "mock")
DETECTORS = ("claude_vision", "hybrid", "yolov8")

# analyze_clip(file, sport, ..., video_metadata) -> response dict
AnalyzeFn = Callable[..., dict]


def _make_file(filename: str) -> SimpleNamespace:
    """Minimal UploadFile stand-in (the mock path only reads filename/content_type)."""
    return SimpleNamespace(filename=filename, content_type="video/mp4")


def _video_metadata(video_path: str) -> dict | None:
    if not video_path:
        return None
    path = Path(video_path)
    size = path.stat().st_size if path.exists() else 0
    return {"stored_path": str(path), "size_bytes": size}


def _predict_clip(clip, run_params: dict, analyze_fn: AnalyzeFn) -> Prediction:
    video_path = str(run_params.get("video_path", ""))
    response = analyze_fn(
        file=_make_file(str(run_params.get("filename") or f"{clip.clip_id}.mp4")),
        sport=clip.sport or "basketball",
        original_call=str(run_params.get("original_call", "")),
        video_metadata=_video_metadata(video_path),
    )
    parsed = prediction_from_response(response)
    # analyze_clip computes its own hash-based clip_id; re-key to the labeled id
    # so the report joins correctly.
    return Prediction(
        clip_id=clip.clip_id,
        predicted_verdict=parsed.predicted_verdict,
        confidence=parsed.confidence,
    )


def _restore_env(key: str, previous: str | None) -> None:
    if previous is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = previous


def run_evaluation(
    dataset_path: str | Path,
    provider: str = "mock",
    detector: str = "claude_vision",
    analyze_fn: AnalyzeFn | None = None,
) -> EvaluationReport:
    """Run the pipeline over a labeled dataset and compute an EvaluationReport."""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider {provider!r}; expected one of {PROVIDERS}.")
    if detector not in DETECTORS:
        raise ValueError(f"Unknown detector {detector!r}; expected one of {DETECTORS}.")

    if analyze_fn is None:
        from services.ai_analyzer import analyze_clip as analyze_fn  # lazy: avoid heavy import for --help

    labeled = load_labeled_clips(dataset_path)
    rows = json.loads(Path(dataset_path).read_text())
    run_params_by_id = {str(row["clip_id"]): row for row in rows}

    prev_provider = os.environ.get("AI_PROVIDER")
    prev_detector = os.environ.get("DETECTOR")
    os.environ["AI_PROVIDER"] = provider
    os.environ["DETECTOR"] = detector
    try:
        predictions = [
            _predict_clip(clip, run_params_by_id.get(clip.clip_id, {}), analyze_fn)
            for clip in labeled
        ]
    finally:
        _restore_env("AI_PROVIDER", prev_provider)
        _restore_env("DETECTOR", prev_detector)

    return evaluate_predictions(labeled, predictions)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evaluation",
        description="Benchmark RefCheck AI verdicts against a labeled clip dataset.",
    )
    parser.add_argument("--dataset", required=True, help="Path to the labeled dataset JSON.")
    parser.add_argument("--output", required=True, help="Path to write the EvaluationReport JSON.")
    parser.add_argument("--provider", default="mock", choices=PROVIDERS, help="AI provider.")
    parser.add_argument(
        "--detector", default="claude_vision", choices=DETECTORS, help="Perception detector."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_evaluation(args.dataset, provider=args.provider, detector=args.detector)

    output = Path(args.output)
    if output.parent != Path(""):
        output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), indent=2))

    print(
        f"Evaluated {report.count} clips | accuracy={report.accuracy:.3f} "
        f"| cohens_kappa={report.cohens_kappa:.3f}"
    )
    print(f"Report written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
