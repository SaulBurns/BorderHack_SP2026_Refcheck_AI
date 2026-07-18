"""Evaluation runner: turn records into an EvaluationReport (Phase 9)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from evaluation.metrics import (
    accuracy,
    brier_score,
    cohens_kappa,
    confidence_by_correctness,
    confusion_matrix,
    expected_calibration_error,
    macro_averages,
    matthews_corrcoef,
    mean_confidence,
    micro_averages,
    per_class_metrics,
    reliability_bins,
)
from evaluation.models import (
    EvaluationRecord,
    LabeledClip,
    Prediction,
    build_records,
    validate_verdict,
)


@dataclass(frozen=True)
class EvaluationReport:
    count: int
    accuracy: float
    cohens_kappa: float
    mean_confidence: float
    confidence_correct: float
    confidence_incorrect: float
    confusion_matrix: dict
    per_class: dict
    # Sprint 5 additions (default-populated so existing construction stays valid).
    macro: dict = field(default_factory=dict)
    micro: dict = field(default_factory=dict)
    ece: float = 0.0
    reliability: list = field(default_factory=list)
    # Sprint 14 additions (proper scoring rule + robust agreement).
    brier: float = 0.0
    mcc: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(records: list[EvaluationRecord]) -> EvaluationReport:
    confidence = confidence_by_correctness(records)
    return EvaluationReport(
        count=len(records),
        accuracy=accuracy(records),
        cohens_kappa=cohens_kappa(records),
        mean_confidence=mean_confidence(records),
        confidence_correct=confidence["correct"],
        confidence_incorrect=confidence["incorrect"],
        confusion_matrix=confusion_matrix(records),
        per_class=per_class_metrics(records),
        macro=macro_averages(records),
        micro=micro_averages(records),
        ece=expected_calibration_error(records),
        reliability=reliability_bins(records),
        brier=brier_score(records),
        mcc=matthews_corrcoef(records),
    )


def evaluate_predictions(
    labeled: list[LabeledClip],
    predictions: list[Prediction],
) -> EvaluationReport:
    return evaluate(build_records(labeled, predictions))


def load_labeled_clips(path: str | Path) -> list[LabeledClip]:
    """Load labeled clips from a JSON array file."""
    rows = json.loads(Path(path).read_text())
    return [
        LabeledClip(
            clip_id=str(row["clip_id"]),
            sport=str(row.get("sport", "")),
            ground_truth_verdict=validate_verdict(str(row["ground_truth_verdict"])),
            notes=str(row.get("notes", "")),
        )
        for row in rows
    ]
