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
]
