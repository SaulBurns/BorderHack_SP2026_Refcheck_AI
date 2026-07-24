"""Officiating-accuracy evaluation framework (Phase 9).

Offline harness that pairs labeled ground-truth verdicts with pipeline
predictions and computes accuracy + agreement metrics.

Public API:
    LabeledClip, Prediction, EvaluationRecord
    prediction_from_response, build_records
    evaluate, evaluate_predictions, load_labeled_clips, EvaluationReport
"""

from evaluation.models import (
    VERDICTS,
    EvaluationError,
    EvaluationRecord,
    LabeledClip,
    Prediction,
    build_records,
    prediction_from_response,
    validate_verdict,
)
from evaluation.runner import (
    EvaluationReport,
    evaluate,
    evaluate_predictions,
    load_labeled_clips,
)
from evaluation.latency import LatencySummary, summarize_latencies
from evaluation.benchmark import (
    STANDARD_COMBOS,
    BenchmarkReport,
    BenchmarkResult,
    ProviderCombo,
    resolve_combo,
    run_benchmark,
)
from evaluation.cost import PRICING, CostSummary, TokenUsage
from evaluation.report import render_html, render_markdown

__all__ = [
    "VERDICTS",
    "EvaluationError",
    "EvaluationRecord",
    "LabeledClip",
    "Prediction",
    "build_records",
    "prediction_from_response",
    "validate_verdict",
    "EvaluationReport",
    "evaluate",
    "evaluate_predictions",
    "load_labeled_clips",
    # Sprint 5 — benchmarking, latency, provider comparison, reports.
    "LatencySummary",
    "summarize_latencies",
    "BenchmarkReport",
    "BenchmarkResult",
    "run_benchmark",
    "render_markdown",
    "render_html",
    # Sprint 17D — provider combos, token usage, cost.
    "ProviderCombo",
    "STANDARD_COMBOS",
    "resolve_combo",
    "TokenUsage",
    "CostSummary",
    "PRICING",
]
