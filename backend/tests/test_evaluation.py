import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest

from evaluation import (
    EvaluationError,
    EvaluationRecord,
    LabeledClip,
    Prediction,
    build_records,
    evaluate,
    evaluate_predictions,
    load_labeled_clips,
    prediction_from_response,
)
from evaluation.metrics import (
    accuracy,
    cohens_kappa,
    confidence_by_correctness,
    confusion_matrix,
    mean_confidence,
    per_class_metrics,
)


def _rec(gt, pred, conf=0.7):
    return EvaluationRecord(clip_id="c", ground_truth=gt, predicted=pred, confidence=conf)


_MIXED = [
    _rec("fair_call", "fair_call", 0.9),
    _rec("fair_call", "bad_call", 0.6),
    _rec("bad_call", "bad_call", 0.8),
    _rec("inconclusive", "inconclusive", 0.7),
]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_accuracy():
    assert accuracy(_MIXED) == 0.75

def test_accuracy_empty_is_zero():
    assert accuracy([]) == 0.0

def test_accuracy_perfect_and_zero():
    assert accuracy([_rec("fair_call", "fair_call")]) == 1.0
    assert accuracy([_rec("fair_call", "bad_call")]) == 0.0

def test_confusion_matrix():
    cm = confusion_matrix(_MIXED)
    assert cm["fair_call"]["fair_call"] == 1
    assert cm["fair_call"]["bad_call"] == 1
    assert cm["bad_call"]["bad_call"] == 1
    assert cm["inconclusive"]["inconclusive"] == 1
    # zero-filled elsewhere
    assert cm["bad_call"]["fair_call"] == 0

def test_per_class_metrics():
    pc = per_class_metrics(_MIXED)
    assert pc["fair_call"]["support"] == 2
    assert pc["fair_call"]["precision"] == 1.0
    assert pc["fair_call"]["recall"] == 0.5
    assert pc["bad_call"]["precision"] == 0.5
    assert pc["bad_call"]["recall"] == 1.0
    assert pc["inconclusive"]["f1"] == 1.0

def test_cohens_kappa_value():
    # po=0.75, pe=0.3125 -> kappa = 0.4375/0.6875
    assert cohens_kappa(_MIXED) == pytest.approx(0.4375 / 0.6875, rel=1e-6)

def test_cohens_kappa_perfect():
    perfect = [_rec("fair_call", "fair_call"), _rec("bad_call", "bad_call")]
    assert cohens_kappa(perfect) == 1.0

def test_mean_confidence():
    assert mean_confidence(_MIXED) == pytest.approx(0.75)

def test_confidence_by_correctness():
    conf = confidence_by_correctness(_MIXED)
    assert conf["correct"] == pytest.approx((0.9 + 0.8 + 0.7) / 3)
    assert conf["incorrect"] == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# Records / predictions
# ---------------------------------------------------------------------------

def test_prediction_from_response():
    response = {"clip_id": "abc", "verdict": {"verdict": "bad_call", "confidence": 0.82}}
    pred = prediction_from_response(response)
    assert pred.clip_id == "abc"
    assert pred.predicted_verdict == "bad_call"
    assert pred.confidence == 0.82

def test_prediction_from_response_invalid_verdict_raises():
    with pytest.raises(EvaluationError):
        prediction_from_response({"clip_id": "x", "verdict": {"verdict": "maybe", "confidence": 0.5}})

def test_build_records_joins_by_clip_id():
    labeled = [LabeledClip("c1", "basketball", "fair_call"), LabeledClip("c2", "basketball", "bad_call")]
    preds = [Prediction("c2", "bad_call", 0.7), Prediction("c1", "fair_call", 0.9)]
    records = build_records(labeled, preds)
    assert {r.clip_id for r in records} == {"c1", "c2"}
    assert all(r.correct for r in records)

def test_build_records_missing_prediction_raises():
    labeled = [LabeledClip("c1", "basketball", "fair_call")]
    with pytest.raises(EvaluationError):
        build_records(labeled, [])


# ---------------------------------------------------------------------------
# Runner / report
# ---------------------------------------------------------------------------

def test_evaluate_report_fields():
    report = evaluate(_MIXED)
    assert report.count == 4
    assert report.accuracy == 0.75
    assert "fair_call" in report.confusion_matrix
    assert report.to_dict()["accuracy"] == 0.75

def test_evaluate_predictions_end_to_end():
    labeled = [LabeledClip("c1", "basketball", "fair_call"), LabeledClip("c2", "basketball", "bad_call")]
    preds = [Prediction("c1", "fair_call", 0.9), Prediction("c2", "fair_call", 0.4)]
    report = evaluate_predictions(labeled, preds)
    assert report.count == 2
    assert report.accuracy == 0.5

def test_load_labeled_clips_from_example_file():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "eval", "labeled_clips.example.json")
    clips = load_labeled_clips(path)
    assert len(clips) == 3
    assert {c.ground_truth_verdict for c in clips} == {"bad_call", "fair_call", "inconclusive"}

def test_load_labeled_clips_invalid_verdict_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"clip_id": "x", "sport": "basketball", "ground_truth_verdict": "nope"}]))
    with pytest.raises(EvaluationError):
        load_labeled_clips(bad)
