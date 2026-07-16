import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from evaluation.benchmark import BenchmarkReport, run_benchmark
from evaluation.latency import summarize_latencies
from evaluation.metrics import (
    expected_calibration_error,
    macro_averages,
    micro_averages,
    reliability_bins,
)
from evaluation.models import EvaluationRecord
from evaluation.report import render_html, render_markdown


def _rec(gt, pred, conf=0.7):
    return EvaluationRecord(clip_id="c", ground_truth=gt, predicted=pred, confidence=conf)


# ---------------------------------------------------------------------------
# Macro / micro averages
# ---------------------------------------------------------------------------

def test_macro_averages_ignores_empty_classes_but_averages_over_all():
    # Perfect on two classes; the third has zero support (p=r=f1=0).
    records = [_rec("fair_call", "fair_call"), _rec("bad_call", "bad_call")]
    macro = macro_averages(records)
    assert macro["f1"] == pytest.approx(2 / 3)  # (1 + 1 + 0) / 3
    assert macro["precision"] == pytest.approx(2 / 3)

def test_micro_averages_equal_accuracy_for_single_label():
    records = [_rec("fair_call", "fair_call"), _rec("bad_call", "fair_call")]  # 50%
    micro = micro_averages(records)
    assert micro["precision"] == micro["recall"] == micro["f1"] == 0.5


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

def test_reliability_bins_group_by_confidence():
    records = [_rec("fair_call", "fair_call", 0.9), _rec("fair_call", "bad_call", 0.9)]
    bins = reliability_bins(records, n_bins=10)
    top = bins[-1]  # 0.9–1.0
    assert top["count"] == 2
    assert top["avg_confidence"] == pytest.approx(0.9)
    assert top["accuracy"] == pytest.approx(0.5)

def test_expected_calibration_error():
    # Both at conf 0.9, one correct one wrong -> |0.5 - 0.9| weighted by all = 0.4.
    records = [_rec("fair_call", "fair_call", 0.9), _rec("fair_call", "bad_call", 0.9)]
    assert expected_calibration_error(records) == pytest.approx(0.4)

def test_ece_perfectly_calibrated_is_zero():
    records = [_rec("fair_call", "fair_call", 1.0), _rec("fair_call", "bad_call", 0.0)]
    assert expected_calibration_error(records) == pytest.approx(0.0)

def test_ece_empty_is_zero():
    assert expected_calibration_error([]) == 0.0


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------

def test_summarize_latencies():
    s = summarize_latencies([10.0, 20.0, 30.0])
    assert s.count == 3
    assert s.mean_ms == pytest.approx(20.0)
    assert s.p50_ms == pytest.approx(20.0)
    assert s.min_ms == 10.0 and s.max_ms == 30.0
    assert s.p95_ms == pytest.approx(29.0)  # nearest-rank interpolation
    assert s.total_ms == pytest.approx(60.0)

def test_summarize_latencies_empty():
    s = summarize_latencies([])
    assert s.count == 0 and s.mean_ms == 0.0 and s.p95_ms == 0.0


# ---------------------------------------------------------------------------
# Benchmark (provider comparison) with an injected analyze_fn (offline, fast)
# ---------------------------------------------------------------------------

def _write_dataset(tmp_path):
    rows = [
        {"clip_id": "c1", "sport": "basketball", "ground_truth_verdict": "fair_call"},
        {"clip_id": "c2", "sport": "basketball", "ground_truth_verdict": "bad_call"},
    ]
    path = tmp_path / "ds.json"
    path.write_text(json.dumps(rows))
    return path

# mock is perfect; gemini misses c2 -> the comparison must reflect the difference.
_VERDICT_BY_PROVIDER = {
    "mock": {"c1": "fair_call", "c2": "bad_call"},
    "gemini": {"c1": "fair_call", "c2": "fair_call"},
}

def _provider_aware_analyze(**kwargs):
    provider = os.environ.get("AI_PROVIDER", "mock")
    clip_id = kwargs["file"].filename.replace(".mp4", "")
    verdict = _VERDICT_BY_PROVIDER[provider][clip_id]
    return {"clip_id": "hash", "verdict": {"verdict": verdict, "confidence": 0.8}}

def test_run_benchmark_compares_providers(tmp_path):
    ds = _write_dataset(tmp_path)
    report = run_benchmark(ds, ["mock", "gemini"], analyze_fn=_provider_aware_analyze)
    assert isinstance(report, BenchmarkReport)
    assert report.clip_count == 2
    assert [r.provider for r in report.results] == ["mock", "gemini"]
    by_provider = {r.provider: r for r in report.results}
    assert by_provider["mock"].evaluation.accuracy == 1.0
    assert by_provider["gemini"].evaluation.accuracy == 0.5
    # gemini mislabeled the bad_call clip as fair_call.
    assert by_provider["gemini"].evaluation.confusion_matrix["bad_call"]["fair_call"] == 1
    # latency captured per provider.
    assert by_provider["mock"].latency.count == 2
    assert by_provider["gemini"].latency.mean_ms >= 0.0

def test_run_benchmark_rejects_unknown_provider(tmp_path):
    ds = _write_dataset(tmp_path)
    with pytest.raises(ValueError):
        run_benchmark(ds, ["openai"], analyze_fn=_provider_aware_analyze)

def test_run_benchmark_requires_at_least_one_provider(tmp_path):
    ds = _write_dataset(tmp_path)
    with pytest.raises(ValueError):
        run_benchmark(ds, [], analyze_fn=_provider_aware_analyze)

def test_benchmark_report_to_dict_shape(tmp_path):
    ds = _write_dataset(tmp_path)
    report = run_benchmark(ds, ["mock"], analyze_fn=_provider_aware_analyze)
    d = report.to_dict()
    assert d["clip_count"] == 2
    result = d["results"][0]
    assert result["provider"] == "mock"
    assert "evaluation" in result and "latency" in result
    assert "ece" in result["evaluation"] and "macro" in result["evaluation"]
    assert result["latency"]["count"] == 2


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _two_provider_report(tmp_path):
    ds = _write_dataset(tmp_path)
    return run_benchmark(ds, ["mock", "gemini"], analyze_fn=_provider_aware_analyze)

def test_render_markdown_has_all_sections(tmp_path):
    md = render_markdown(_two_provider_report(tmp_path))
    assert "# RefCheck AI — Evaluation Benchmark" in md
    assert "## Provider comparison" in md
    assert "| Provider | Accuracy | Macro F1 | Kappa | ECE |" in md
    assert "## Provider: mock" in md and "## Provider: gemini" in md
    assert "Confusion matrix" in md
    assert "Per-class metrics" in md
    assert "Confidence calibration" in md

def test_render_html_is_self_contained(tmp_path):
    html = render_html(_two_provider_report(tmp_path))
    assert html.startswith("<!doctype html>")
    assert "<style>" in html  # inline CSS, no external deps
    assert "Provider comparison" in html
    assert "Confusion matrix" in html
    assert ">mock<" in html and ">gemini<" in html
    assert "cm-hit" in html  # confusion-matrix diagonal shading present
