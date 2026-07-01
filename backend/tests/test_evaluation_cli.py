import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest

from evaluation.cli import _make_file, _video_metadata, main, run_evaluation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(clip_id, gt, sport="basketball", **extra):
    return {"clip_id": clip_id, "sport": sport, "ground_truth_verdict": gt, **extra}

def _write_dataset(tmp_path, rows):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(rows))
    return path

def _resp(verdict, confidence=0.8, clip_id="hash-computed"):
    return {"clip_id": clip_id, "verdict": {"verdict": verdict, "confidence": confidence}}

class _SeqAnalyze:
    """Returns queued responses in call order (stand-in for analyze_clip)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._index = 0

    def __call__(self, **kwargs):
        response = self._responses[self._index]
        self._index += 1
        return response


# ---------------------------------------------------------------------------
# run_evaluation — metrics
# ---------------------------------------------------------------------------

def test_run_evaluation_perfect(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "fair_call"), _row("c2", "bad_call"), _row("c3", "inconclusive")])
    fake = _SeqAnalyze([_resp("fair_call"), _resp("bad_call"), _resp("inconclusive")])
    report = run_evaluation(ds, provider="mock", detector="claude_vision", analyze_fn=fake)
    assert report.count == 3
    assert report.accuracy == 1.0
    assert report.cohens_kappa == 1.0

def test_run_evaluation_partial_accuracy_and_confusion(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "fair_call"), _row("c2", "bad_call")])
    fake = _SeqAnalyze([_resp("fair_call"), _resp("fair_call")])  # c2 wrong
    report = run_evaluation(ds, analyze_fn=fake)
    assert report.accuracy == 0.5
    assert report.confusion_matrix["bad_call"]["fair_call"] == 1
    assert report.per_class["fair_call"]["recall"] == 1.0

def test_run_evaluation_rekeys_predictions(tmp_path):
    # analyze_clip returns its own clip_id; the runner must re-key to the label.
    ds = _write_dataset(tmp_path, [_row("c1", "fair_call")])
    fake = _SeqAnalyze([_resp("fair_call", clip_id="TOTALLY-DIFFERENT")])
    report = run_evaluation(ds, analyze_fn=fake)
    assert report.count == 1
    assert report.accuracy == 1.0


# ---------------------------------------------------------------------------
# run_evaluation — provider/detector handling
# ---------------------------------------------------------------------------

def test_invalid_provider_raises(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "fair_call")])
    with pytest.raises(ValueError):
        run_evaluation(ds, provider="openai", analyze_fn=_SeqAnalyze([_resp("fair_call")]))

def test_invalid_detector_raises(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "fair_call")])
    with pytest.raises(ValueError):
        run_evaluation(ds, detector="magic_eyes", analyze_fn=_SeqAnalyze([_resp("fair_call")]))

def test_env_set_during_run_and_restored(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("DETECTOR", raising=False)
    captured = {}

    def fake(**kwargs):
        captured["provider"] = os.environ.get("AI_PROVIDER")
        captured["detector"] = os.environ.get("DETECTOR")
        return _resp("fair_call")

    ds = _write_dataset(tmp_path, [_row("c1", "fair_call")])
    run_evaluation(ds, provider="mock", detector="hybrid", analyze_fn=fake)
    # env was set during the run...
    assert captured["provider"] == "mock"
    assert captured["detector"] == "hybrid"
    # ...and restored afterward (was unset -> removed).
    assert os.environ.get("AI_PROVIDER") is None
    assert os.environ.get("DETECTOR") is None

def test_run_evaluation_passes_video_metadata_and_call(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"1234")
    ds = _write_dataset(tmp_path, [
        _row("c1", "fair_call", video_path=str(video), original_call="blocking foul"),
    ])
    captured = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return _resp("fair_call")

    run_evaluation(ds, analyze_fn=fake)
    assert captured["video_metadata"]["stored_path"] == str(video)
    assert captured["video_metadata"]["size_bytes"] == 4
    assert captured["original_call"] == "blocking foul"
    assert captured["sport"] == "basketball"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_video_metadata_none_when_empty():
    assert _video_metadata("") is None

def test_video_metadata_missing_file_size_zero(tmp_path):
    md = _video_metadata(str(tmp_path / "nope.mp4"))
    assert md["size_bytes"] == 0

def test_make_file_has_required_attrs():
    fobj = _make_file("x.mp4")
    assert fobj.filename == "x.mp4"
    assert fobj.content_type == "video/mp4"


# ---------------------------------------------------------------------------
# main() — end-to-end offline (real analyze_clip in mock mode) + JSON output
# ---------------------------------------------------------------------------

def test_main_writes_report_json_offline(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "inconclusive")])
    out = tmp_path / "report.json"
    return_code = main(["--dataset", str(ds), "--output", str(out), "--provider", "mock"])
    assert return_code == 0
    assert out.exists()

    data = json.loads(out.read_text())
    for key in (
        "count", "accuracy", "cohens_kappa", "confusion_matrix", "per_class",
        "mean_confidence", "confidence_correct", "confidence_incorrect",
    ):
        assert key in data, f"missing {key} in report"
    assert data["count"] == 1
    assert set(data["per_class"]["fair_call"]) >= {"precision", "recall", "f1", "support"}

def test_main_creates_nested_output_dir(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "inconclusive")])
    out = tmp_path / "nested" / "dir" / "report.json"
    assert main(["--dataset", str(ds), "--output", str(out), "--provider", "mock"]) == 0
    assert out.exists()

def test_main_rejects_invalid_provider(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "fair_call")])
    with pytest.raises(SystemExit):
        main(["--dataset", str(ds), "--output", str(tmp_path / "o.json"), "--provider", "openai"])

def test_main_rejects_invalid_detector(tmp_path):
    ds = _write_dataset(tmp_path, [_row("c1", "fair_call")])
    with pytest.raises(SystemExit):
        main(["--dataset", str(ds), "--output", str(tmp_path / "o.json"), "--detector", "magic"])
