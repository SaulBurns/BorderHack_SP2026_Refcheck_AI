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


def macro_averages(records: list[EvaluationRecord]) -> dict[str, float]:
    """Unweighted mean of per-class precision/recall/F1 (treats classes equally)."""
    per_class = per_class_metrics(records)
    n = len(VERDICTS)
    return {
        metric: sum(per_class[v][metric] for v in VERDICTS) / n
        for metric in ("precision", "recall", "f1")
    }


def micro_averages(records: list[EvaluationRecord]) -> dict[str, float]:
    """Globally-pooled precision/recall/F1. For single-label multiclass these all
    equal accuracy, but we compute them from pooled TP/FP/FN so the derivation is
    explicit and stays correct if the label model ever changes."""
    true_positive = sum(1 for r in records if r.ground_truth == r.predicted)
    total = len(records)
    # In single-label multiclass every prediction is exactly one class, so pooled
    # FP == FN == total - TP, making precision == recall == f1.
    precision = true_positive / total if total else 0.0
    return {"precision": precision, "recall": precision, "f1": precision}


def reliability_bins(
    records: list[EvaluationRecord], n_bins: int = 10
) -> list[dict[str, float]]:
    """Calibration reliability table: for each confidence bin, the mean predicted
    confidence vs. the observed accuracy. A well-calibrated model has these equal."""
    bins: list[dict[str, float]] = []
    for i in range(n_bins):
        low = i / n_bins
        high = (i + 1) / n_bins
        # Include the top edge (1.0) in the final bin.
        in_bin = [
            r
            for r in records
            if (r.confidence >= low and (r.confidence < high or (i == n_bins - 1 and r.confidence <= high)))
        ]
        count = len(in_bin)
        bins.append(
            {
                "bin_lower": round(low, 3),
                "bin_upper": round(high, 3),
                "count": count,
                "avg_confidence": (sum(r.confidence for r in in_bin) / count) if count else 0.0,
                "accuracy": (sum(1 for r in in_bin if r.correct) / count) if count else 0.0,
            }
        )
    return bins


def expected_calibration_error(records: list[EvaluationRecord], n_bins: int = 10) -> float:
    """Expected Calibration Error: confidence-weighted average gap between predicted
    confidence and observed accuracy across bins (0 = perfectly calibrated)."""
    total = len(records)
    if total == 0:
        return 0.0
    return sum(
        (b["count"] / total) * abs(b["accuracy"] - b["avg_confidence"])
        for b in reliability_bins(records, n_bins)
        if b["count"]
    )


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
