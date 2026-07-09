import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import services.ai_analyzer as ai
import scripts.run_demo_suite as suite
from scripts.run_demo_suite import (
    DemoClip,
    ManifestError,
    build_record,
    build_report,
    load_manifest,
    main,
    render_markdown,
    run_clip,
    select_clips,
    validate_clip,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _valid_row(**overrides):
    row = {
        "clip_id": "clip_01",
        "sport": "basketball",
        "video_path": "clip_01.mp4",
        "original_call": "Blocking foul",
    }
    row.update(overrides)
    return row


def _make_manifest(tmp_path, rows, with_media=True):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(rows))
    if with_media:
        for row in rows:
            (tmp_path / row["video_path"]).write_bytes(b"\x00\x00\x00\x1cftypmp42")
    return manifest


# ---------------------------------------------------------------------------
# Manifest parsing / validation
# ---------------------------------------------------------------------------

def test_validate_clip_valid():
    clip = validate_clip(_valid_row(game_date="2024-12-25", home_team="LAL", away_team="BOS"))
    assert clip.clip_id == "clip_01"
    assert clip.metadata_hints() == {
        "clip_date_hint": "2024-12-25",
        "home_team_hint": "LAL",
        "away_team_hint": "BOS",
    }

@pytest.mark.parametrize("field", ["clip_id", "sport", "video_path", "original_call"])
def test_validate_clip_missing_required_field(field):
    row = _valid_row()
    del row[field]
    with pytest.raises(ManifestError) as exc:
        validate_clip(row)
    assert field in str(exc.value)

def test_validate_clip_optional_hints_absent():
    clip = validate_clip(_valid_row())
    assert clip.expected_verdict is None
    assert clip.metadata_hints() == {"clip_date_hint": None, "home_team_hint": None, "away_team_hint": None}

def test_load_manifest_roundtrip(tmp_path):
    manifest = _make_manifest(tmp_path, [_valid_row(), _valid_row(clip_id="clip_02", video_path="clip_02.mp4")])
    clips = load_manifest(manifest)
    assert [c.clip_id for c in clips] == ["clip_01", "clip_02"]

def test_load_manifest_rejects_empty(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text("[]")
    with pytest.raises(ManifestError):
        load_manifest(manifest)

def test_load_manifest_rejects_bad_json(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text("{not json")
    with pytest.raises(ManifestError):
        load_manifest(manifest)

def test_load_manifest_missing_file(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# Clip selection (--clip-id / --limit)
# ---------------------------------------------------------------------------

def _clips():
    return [
        DemoClip(clip_id="a", sport="basketball", video_path="a.mp4", original_call="x"),
        DemoClip(clip_id="b", sport="basketball", video_path="b.mp4", original_call="y"),
        DemoClip(clip_id="c", sport="basketball", video_path="c.mp4", original_call="z"),
    ]

def test_select_clip_by_id():
    assert [c.clip_id for c in select_clips(_clips(), "b", None)] == ["b"]

def test_select_clip_by_id_unknown_raises():
    with pytest.raises(ManifestError):
        select_clips(_clips(), "zzz", None)

def test_select_clip_limit():
    assert [c.clip_id for c in select_clips(_clips(), None, 2)] == ["a", "b"]

def test_select_clip_no_filter():
    assert len(select_clips(_clips(), None, None)) == 3


# ---------------------------------------------------------------------------
# Record building / real_pipeline_ran / expected comparison
# ---------------------------------------------------------------------------

def _mock_response(verdict="fair_call"):
    return {
        "clip_id": "clip_01",
        "verdict": {"verdict": verdict, "confidence": 0.7, "cited_rule": {"rule_id": "BLOCK_CHARGE", "section_title": "Legal guarding"}},
        "diagnostics": {"provider_used": "mock", "detector": "mock", "fallback_reason": "AI_PROVIDER is set to mock.",
                        "detections_present": False, "tracking_present": False, "sport_details_source": "perception",
                        "metadata_attempted": True, "metadata_status": "unresolved"},
    }

def _real_response(verdict="fair_call"):
    return {
        "clip_id": "clip_01",
        "verdict": {"verdict": verdict, "confidence": 0.8, "cited_rule": {"rule_id": "R1", "section_title": "Rule one"}},
        "diagnostics": {"provider_used": "anthropic_four_agent", "detector": "claude_vision", "fallback_reason": None,
                        "detections_present": True, "tracking_present": True, "sport_details_source": "detections",
                        "metadata_attempted": True, "metadata_status": "resolved"},
    }

def test_build_record_mock_is_not_real():
    clip = validate_clip(_valid_row(expected_verdict="fair_call"))
    rec = build_record(clip, _mock_response("fair_call"))
    assert rec["real_pipeline_ran"] is False
    assert rec["provider_used"] == "mock"
    assert rec["fallback_reason"] == "AI_PROVIDER is set to mock."
    assert rec["verdict_matches_expected"] is True

def test_build_record_real_is_real():
    clip = validate_clip(_valid_row())
    rec = build_record(clip, _real_response())
    assert rec["real_pipeline_ran"] is True
    assert rec["cited_rule_id"] == "R1"

def test_build_record_expected_mismatch():
    clip = validate_clip(_valid_row(expected_verdict="bad_call"))
    rec = build_record(clip, _mock_response("fair_call"))
    assert rec["verdict_matches_expected"] is False

def test_build_record_expected_synonym_upheld_matches_fair_call():
    clip = validate_clip(_valid_row(expected_verdict="upheld"))
    rec = build_record(clip, _mock_response("fair_call"))
    assert rec["verdict_matches_expected"] is True

def test_build_record_no_expected_omits_comparison():
    clip = validate_clip(_valid_row())
    rec = build_record(clip, _mock_response())
    assert "verdict_matches_expected" not in rec


# ---------------------------------------------------------------------------
# run_clip threads metadata hints and calls the REAL analyze function
# ---------------------------------------------------------------------------

def test_run_clip_calls_real_analyze_and_threads_hints(monkeypatch, tmp_path):
    captured = {}

    def _fake_analyze(*, file, sport, video_metadata):
        captured["video_metadata"] = video_metadata
        captured["sport"] = sport
        return _mock_response()

    monkeypatch.setattr(ai, "analyze_clip", _fake_analyze)
    (tmp_path / "clip_01.mp4").write_bytes(b"\x00\x00\x00\x1cftypmp42")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")  # only used for path resolution base
    clip = validate_clip(_valid_row(video_path=str(tmp_path / "clip_01.mp4"),
                                    game_date="2024-12-25", home_team="LAL", away_team="BOS"))
    rec = run_clip(clip, manifest, provider="mock", detector=None)
    assert rec["status"] == "ok"
    assert captured["sport"] == "basketball"
    assert captured["video_metadata"]["clip_date_hint"] == "2024-12-25"
    assert captured["video_metadata"]["home_team_hint"] == "LAL"
    assert captured["video_metadata"]["away_team_hint"] == "BOS"

def test_run_clip_missing_video_is_error_record(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    clip = validate_clip(_valid_row(video_path="does_not_exist.mp4"))
    rec = run_clip(clip, manifest, provider="mock", detector=None)
    assert rec["status"] == "error"
    assert rec["real_pipeline_ran"] is False
    assert "not found" in rec["fallback_reason"]


# ---------------------------------------------------------------------------
# Aggregate report + markdown
# ---------------------------------------------------------------------------

def test_build_report_aggregates():
    clip = validate_clip(_valid_row(expected_verdict="fair_call"))
    records = [build_record(clip, _mock_response()), build_record(clip, _real_response())]
    report = build_report(records, provider="anthropic", detector="claude_vision")
    s = report["summary"]
    assert s["total_clips"] == 2
    assert s["real_pipeline_runs"] == 1
    assert s["mock_or_fallback_runs"] == 1
    assert s["metadata_resolved"] == 1
    assert s["expected_verdict_matches"] == 2

def test_render_markdown_contains_key_sections():
    clip = validate_clip(_valid_row(expected_verdict="fair_call", notes="baseline"))
    report = build_report([build_record(clip, _mock_response())], provider="mock", detector=None)
    md = render_markdown(report)
    assert "# RefCheck AI — Basketball Demo Suite Report" in md
    assert "## Summary" in md
    assert "clip_01" in md
    assert "Fallback reason" in md
    assert "No clip ran the real pipeline" in md  # all-mock warning banner


# ---------------------------------------------------------------------------
# main(): end-to-end mock suite + strict-real behavior
# ---------------------------------------------------------------------------

def test_main_mock_suite_writes_reports(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    rows = [_valid_row(), _valid_row(clip_id="clip_02", video_path="clip_02.mp4")]
    manifest = _make_manifest(tmp_path, rows)
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"
    rc = main(["--manifest", str(manifest), "--provider", "mock",
               "--output-json", str(json_out), "--output-md", str(md_out)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DEMO SUITE" in out
    data = json.loads(json_out.read_text())
    assert data["summary"]["total_clips"] == 2
    assert data["summary"]["real_pipeline_runs"] == 0
    assert md_out.exists()
    assert all(c["real_pipeline_ran"] is False for c in data["clips"])
    assert all(c["fallback_reason"] for c in data["clips"])

def test_main_clip_id_runs_single(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    rows = [_valid_row(), _valid_row(clip_id="clip_02", video_path="clip_02.mp4")]
    manifest = _make_manifest(tmp_path, rows)
    json_out = tmp_path / "r.json"
    rc = main(["--manifest", str(manifest), "--provider", "mock", "--clip-id", "clip_02",
               "--output-json", str(json_out), "--output-md", str(tmp_path / "r.md")])
    assert rc == 0
    data = json.loads(json_out.read_text())
    assert [c["clip_id"] for c in data["clips"]] == ["clip_02"]

def test_main_strict_real_fails_when_falls_back_to_mock(monkeypatch, tmp_path):
    # Env prerequisites satisfied (so the up-front gate passes) but the pipeline
    # still returns mock → strict mode must fail loudly at the end.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # Force the up-front env gate to pass so we exercise the end-of-run strict
    # check (a clip that still fell back to mock must fail the suite).
    monkeypatch.setattr(suite, "preflight_blockers", lambda checks: [])
    monkeypatch.setattr(ai, "analyze_clip", lambda **k: _mock_response())
    manifest = _make_manifest(tmp_path, [_valid_row()])
    rc = main(["--manifest", str(manifest), "--provider", "anthropic",
               "--strict-real", "--output-json", str(tmp_path / "r.json"),
               "--output-md", str(tmp_path / "r.md")])
    assert rc == 3

def test_main_strict_real_blocks_when_env_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    manifest = _make_manifest(tmp_path, [_valid_row()])
    rc = main(["--manifest", str(manifest), "--provider", "anthropic", "--strict-real",
               "--output-json", str(tmp_path / "r.json"), "--output-md", str(tmp_path / "r.md")])
    assert rc == 3
    assert "PREFLIGHT" in capsys.readouterr().out

def test_main_bad_manifest_returns_2(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps([{"clip_id": "x"}]))  # missing required fields
    rc = main(["--manifest", str(manifest), "--provider", "mock"])
    assert rc == 2
