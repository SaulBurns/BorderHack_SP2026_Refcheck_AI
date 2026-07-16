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
from time import perf_counter
from types import SimpleNamespace
from typing import Callable

from evaluation.models import LabeledClip, Prediction, prediction_from_response
from evaluation.runner import EvaluationReport, evaluate_predictions, load_labeled_clips

PROVIDERS = ("anthropic", "gemini", "mock")
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


def _resolve_analyze_fn(analyze_fn: AnalyzeFn | None) -> AnalyzeFn:
    if analyze_fn is not None:
        return analyze_fn
    from services.ai_analyzer import analyze_clip  # lazy: avoid heavy import for --help

    return analyze_clip


def collect_predictions(
    labeled: list[LabeledClip],
    run_params_by_id: dict[str, dict],
    provider: str,
    detector: str,
    analyze_fn: AnalyzeFn,
) -> tuple[list[Prediction], list[float]]:
    """Drive the pipeline for one provider/detector over the labeled clips.

    Sets AI_PROVIDER/DETECTOR for the run and restores them afterward. Returns the
    predictions plus per-clip latencies in milliseconds (used by the benchmark).
    """
    prev_provider = os.environ.get("AI_PROVIDER")
    prev_detector = os.environ.get("DETECTOR")
    os.environ["AI_PROVIDER"] = provider
    os.environ["DETECTOR"] = detector
    predictions: list[Prediction] = []
    latencies_ms: list[float] = []
    try:
        for clip in labeled:
            started = perf_counter()
            prediction = _predict_clip(clip, run_params_by_id.get(clip.clip_id, {}), analyze_fn)
            latencies_ms.append((perf_counter() - started) * 1000)
            predictions.append(prediction)
    finally:
        _restore_env("AI_PROVIDER", prev_provider)
        _restore_env("DETECTOR", prev_detector)
    return predictions, latencies_ms


def _load_dataset(dataset_path: str | Path) -> tuple[list[LabeledClip], dict[str, dict]]:
    labeled = load_labeled_clips(dataset_path)
    rows = json.loads(Path(dataset_path).read_text())
    return labeled, {str(row["clip_id"]): row for row in rows}


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

    analyze_fn = _resolve_analyze_fn(analyze_fn)
    labeled, run_params_by_id = _load_dataset(dataset_path)
    predictions, _ = collect_predictions(labeled, run_params_by_id, provider, detector, analyze_fn)
    return evaluate_predictions(labeled, predictions)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evaluation",
        description="Benchmark RefCheck AI verdicts against a labeled clip dataset.",
    )
    parser.add_argument("--dataset", required=True, help="Path to the labeled dataset JSON.")
    parser.add_argument("--output", required=True, help="Path to write the report JSON.")
    parser.add_argument("--provider", default="mock", choices=PROVIDERS, help="Single AI provider.")
    parser.add_argument(
        "--providers",
        default=None,
        help="Comma-separated providers for a comparison benchmark, e.g. mock,anthropic,gemini.",
    )
    parser.add_argument(
        "--detector", default="claude_vision", choices=DETECTORS, help="Perception detector."
    )
    parser.add_argument("--md", default=None, help="Optional path to write a Markdown report.")
    parser.add_argument("--html", default=None, help="Optional path to write an HTML report.")
    return parser


def _write_file(path: str, content: str) -> None:
    out = Path(path)
    if out.parent != Path(""):
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Lazy import to avoid the benchmark<->cli cycle and keep --help cheap.
    from evaluation.benchmark import run_benchmark
    from evaluation.report import render_html, render_markdown

    comparison_mode = bool(args.providers)
    providers = (
        [p.strip() for p in args.providers.split(",") if p.strip()]
        if comparison_mode
        else [args.provider]
    )

    benchmark = run_benchmark(args.dataset, providers, detector=args.detector)

    # JSON: the full BenchmarkReport for a comparison; the bare EvaluationReport for
    # a single provider (backward compatible with the Phase 9 report schema).
    payload = benchmark.to_dict() if comparison_mode else benchmark.results[0].evaluation.to_dict()
    _write_file(args.output, json.dumps(payload, indent=2))
    if args.md:
        _write_file(args.md, render_markdown(benchmark))
    if args.html:
        _write_file(args.html, render_html(benchmark))

    print(f"Benchmarked {len(providers)} provider(s) over {benchmark.clip_count} clips:")
    for result in benchmark.results:
        ev = result.evaluation
        print(
            f"  {result.provider:>10} | acc={ev.accuracy:.3f} macroF1={ev.macro.get('f1', 0.0):.3f} "
            f"kappa={ev.cohens_kappa:.3f} ece={ev.ece:.3f} mean_ms={result.latency.mean_ms:.1f}"
        )
    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
