"""Accuracy and agreement metrics for the evaluation framework (Phase 9).

Pure functions over EvaluationRecords. Empty input yields zeroed metrics rather
than raising, so a report can always be produced.
"""

from __future__ import annotations

from collections import Counter

from evaluation.models import VERDICTS, EvaluationRecord


def accuracy(records: list[EvaluationRecord]) -> float:
    if not records:
        return 0.0
    return sum(1 for r in records if r.correct) / len(records)


def confusion_matrix(records: list[EvaluationRecord]) -> dict[str, dict[str, int]]:
    """matrix[ground_truth][predicted] = count (zero-filled over all verdicts)."""
    matrix = {gt: {pred: 0 for pred in VERDICTS} for gt in VERDICTS}
    for r in records:
        matrix[r.ground_truth][r.predicted] += 1
    return matrix


def per_class_metrics(records: list[EvaluationRecord]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for verdict in VERDICTS:
        support = sum(1 for r in records if r.ground_truth == verdict)
        predicted_positive = sum(1 for r in records if r.predicted == verdict)
        true_positive = sum(
            1 for r in records if r.ground_truth == verdict and r.predicted == verdict
        )
        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / support if support else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        out[verdict] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    return out


def cohens_kappa(records: list[EvaluationRecord]) -> float:
    """Chance-corrected agreement between ground truth and predictions."""
    n = len(records)
    if n == 0:
        return 0.0
    observed_agreement = accuracy(records)
    gt_counts = Counter(r.ground_truth for r in records)
    pred_counts = Counter(r.predicted for r in records)
    expected_agreement = sum((gt_counts[c] / n) * (pred_counts[c] / n) for c in VERDICTS)
    if expected_agreement >= 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def mean_confidence(records: list[EvaluationRecord]) -> float:
    if not records:
        return 0.0
    return sum(r.confidence for r in records) / len(records)


def confidence_by_correctness(records: list[EvaluationRecord]) -> dict[str, float]:
    """Mean confidence split by whether the prediction was correct (calibration signal)."""
    correct = [r.confidence for r in records if r.correct]
    incorrect = [r.confidence for r in records if not r.correct]
    return {
        "correct": sum(correct) / len(correct) if correct else 0.0,
        "incorrect": sum(incorrect) / len(incorrect) if incorrect else 0.0,
    }
