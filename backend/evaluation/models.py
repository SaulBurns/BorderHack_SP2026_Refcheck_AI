"""Data models for the officiating-accuracy evaluation framework (Phase 9).

Offline, dependency-free: pairs ground-truth verdicts (labeled clips) with
predicted verdicts (from the live pipeline response) into EvaluationRecords.
"""

from __future__ import annotations

from dataclasses import dataclass

VERDICTS = ("fair_call", "bad_call", "inconclusive")


class EvaluationError(ValueError):
    """Raised for invalid evaluation inputs (unknown verdict, missing prediction)."""


@dataclass(frozen=True)
class LabeledClip:
    """A clip with a human-assigned ground-truth verdict."""

    clip_id: str
    sport: str
    ground_truth_verdict: str
    notes: str = ""


@dataclass(frozen=True)
class Prediction:
    """A model-predicted verdict for a clip."""

    clip_id: str
    predicted_verdict: str
    confidence: float


@dataclass(frozen=True)
class EvaluationRecord:
    """A ground-truth/prediction pair for one clip."""

    clip_id: str
    ground_truth: str
    predicted: str
    confidence: float

    @property
    def correct(self) -> bool:
        return self.ground_truth == self.predicted


def validate_verdict(value: str) -> str:
    if value not in VERDICTS:
        raise EvaluationError(f"Unknown verdict {value!r}; expected one of {VERDICTS}.")
    return value


def prediction_from_response(response: dict) -> Prediction:
    """Extract a Prediction from a live AnalyzeResponse dict."""
    verdict = response.get("verdict") or {}
    return Prediction(
        clip_id=str(response.get("clip_id", "")),
        predicted_verdict=validate_verdict(str(verdict.get("verdict"))),
        confidence=float(verdict.get("confidence", 0.0)),
    )


def build_records(
    labeled: list[LabeledClip],
    predictions: list[Prediction],
) -> list[EvaluationRecord]:
    """Join labeled clips with predictions by clip_id."""
    pred_by_clip = {p.clip_id: p for p in predictions}
    records: list[EvaluationRecord] = []
    for clip in labeled:
        pred = pred_by_clip.get(clip.clip_id)
        if pred is None:
            raise EvaluationError(f"No prediction for labeled clip {clip.clip_id!r}.")
        records.append(
            EvaluationRecord(
                clip_id=clip.clip_id,
                ground_truth=validate_verdict(clip.ground_truth_verdict),
                predicted=validate_verdict(pred.predicted_verdict),
                confidence=pred.confidence,
            )
        )
    return records
