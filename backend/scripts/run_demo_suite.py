"""Run a curated suite of demo clips through the real RefCheck pipeline and emit
sponsor-friendly JSON + Markdown reports.

This reuses the hardened single-clip helpers from `demo_analyze.py` (real-run
definition, preflight, metadata-hint threading) so there is exactly one source of
truth for "did the real pipeline run?" — this script never reimplements the
pipeline. It just orchestrates many clips and aggregates.

Examples (run from the `backend/` directory):

    # Sponsor one-liner — runs the curated 10-scenario manifest and writes reports:
    python scripts/run_demo_suite.py

    # Transparent mock suite (default provider is mock; proves the plumbing):
    python scripts/run_demo_suite.py --manifest demo_clips/manifest.json

    # Real Claude-vision suite (needs ANTHROPIC_API_KEY + ffmpeg):
    python scripts/run_demo_suite.py --manifest demo_clips/manifest.json \
        --provider anthropic --detector claude_vision

    # Strict real run — refuse to silently degrade to mock:
    python scripts/run_demo_suite.py --manifest demo_clips/manifest.json \
        --provider anthropic --detector hybrid --strict-real

    # Single clip / first-N:
    python scripts/run_demo_suite.py --manifest demo_clips/manifest.json --clip-id nba_travel_03
    python scripts/run_demo_suite.py --manifest demo_clips/manifest.json --limit 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Allow running directly (python scripts/run_demo_suite.py) from backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Reuse the hardened single-clip helpers — one source of truth for the demo path.
from scripts.demo_analyze import (  # noqa: E402
    PROVIDERS,
    DETECTORS,
    _metadata_hint_source,
    _real_pipeline_ran,
    format_preflight,
    preflight,
    preflight_blockers,
    run_demo,
)

REQUIRED_FIELDS = ("clip_id", "sport", "video_path", "original_call")

# The curated basketball manifest shipped with the repo. Lets sponsors run the
# suite with zero arguments: `python scripts/run_demo_suite.py`.
DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "demo_clips" / "manifest.json"

# Sponsor-friendly synonyms mapped to the pipeline's real verdict vocabulary
# (fair_call / bad_call / inconclusive), so a manifest may say "upheld".
_VERDICT_ALIASES = {
    "upheld": "fair_call",
    "correct": "fair_call",
    "good_call": "fair_call",
    "overturned": "bad_call",
    "incorrect": "bad_call",
    "wrong_call": "bad_call",
    "inconclusive": "inconclusive",
    "unclear": "inconclusive",
    "fair_call": "fair_call",
    "bad_call": "bad_call",
}


class ManifestError(ValueError):
    """Raised for a malformed manifest or manifest entry."""


# Expected-confidence bands: label -> (inclusive low, exclusive high).
_CONFIDENCE_BANDS = {
    "high": (0.75, 1.01),
    "medium": (0.50, 0.75),
    "low": (0.0, 0.50),
}


@dataclass(frozen=True)
class DemoClip:
    clip_id: str
    sport: str
    video_path: str
    original_call: str
    scenario: str | None = None
    expected_verdict: str | None = None
    expected_rule_id: str | None = None
    rule_citation: str | None = None
    expected_confidence: str | None = None
    game_date: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    notes: str | None = None

    def metadata_hints(self) -> dict:
        return {
            "clip_date_hint": self.game_date,
            "home_team_hint": self.home_team,
            "away_team_hint": self.away_team,
        }


# ---------------------------------------------------------------------------
# Manifest loading / validation
# ---------------------------------------------------------------------------

def validate_clip(row: dict, index: int = 0) -> DemoClip:
    if not isinstance(row, dict):
        raise ManifestError(f"Manifest entry #{index} must be an object, got {type(row).__name__}.")
    missing = [f for f in REQUIRED_FIELDS if not str(row.get(f, "")).strip()]
    if missing:
        clip_id = row.get("clip_id", f"#{index}")
        raise ManifestError(f"Manifest entry {clip_id!r} is missing required field(s): {', '.join(missing)}.")
    def _opt(field: str) -> str | None:
        return str(row[field]) if row.get(field) else None

    return DemoClip(
        clip_id=str(row["clip_id"]),
        sport=str(row["sport"]),
        video_path=str(row["video_path"]),
        original_call=str(row["original_call"]),
        scenario=_opt("scenario"),
        expected_verdict=_opt("expected_verdict"),
        expected_rule_id=_opt("expected_rule_id"),
        rule_citation=_opt("rule_citation"),
        expected_confidence=_opt("expected_confidence"),
        game_date=_opt("game_date"),
        home_team=_opt("home_team"),
        away_team=_opt("away_team"),
        notes=_opt("notes"),
    )


def load_manifest(path: str | Path) -> list[DemoClip]:
    manifest_path = Path(path).expanduser()
    if not manifest_path.is_file():
        raise ManifestError(f"Manifest not found: {manifest_path}")
    try:
        rows = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Manifest is not valid JSON: {exc}") from exc
    if not isinstance(rows, list) or not rows:
        raise ManifestError("Manifest must be a non-empty JSON array of clip entries.")
    return [validate_clip(row, i) for i, row in enumerate(rows)]


def resolve_video_path(video_path: str, manifest_path: str | Path) -> Path:
    """Resolve a manifest video_path against cwd, the manifest dir, or its parent."""
    raw = Path(video_path).expanduser()
    if raw.is_absolute():
        return raw
    manifest_dir = Path(manifest_path).expanduser().resolve().parent
    candidates = [Path.cwd() / raw, manifest_dir / raw, manifest_dir.parent / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]  # first (cwd-relative); run_demo will report if missing


def select_clips(clips: list[DemoClip], clip_id: str | None, limit: int | None) -> list[DemoClip]:
    if clip_id:
        selected = [c for c in clips if c.clip_id == clip_id]
        if not selected:
            raise ManifestError(f"No manifest entry with clip_id {clip_id!r}.")
        return selected
    if limit is not None and limit >= 0:
        return clips[:limit]
    return clips


# ---------------------------------------------------------------------------
# Per-clip run + record
# ---------------------------------------------------------------------------

def _normalize_verdict(value: str | None) -> str | None:
    if not value:
        return None
    return _VERDICT_ALIASES.get(value.strip().lower(), value.strip().lower())


def _confidence_meets_expectation(expected: str | None, actual) -> bool | None:
    """Whether `actual` falls in the band named by `expected` (high/medium/low)."""
    band = _CONFIDENCE_BANDS.get((expected or "").strip().lower())
    if band is None or not isinstance(actual, (int, float)):
        return None
    low, high = band
    return low <= actual < high


def build_record(clip: DemoClip, response: dict) -> dict:
    diag = response.get("diagnostics", {}) or {}
    verdict = response.get("verdict", {}) or {}
    rule = verdict.get("cited_rule", {}) or {}
    actual_verdict = verdict.get("verdict")
    actual_confidence = verdict.get("confidence")
    cited_rule_id = rule.get("rule_id")
    real_ran = _real_pipeline_ran(diag)

    record = {
        "clip_id": clip.clip_id,
        "sport": clip.sport,
        "scenario": clip.scenario,
        "video_path": clip.video_path,
        "original_call": clip.original_call,
        "notes": clip.notes,
        # curated expectations (from the manifest)
        "rule_citation": clip.rule_citation,
        "expected_confidence": clip.expected_confidence,
        # pipeline outcome
        "provider_used": diag.get("provider_used"),
        "detector": diag.get("detector"),
        "fallback_reason": diag.get("fallback_reason"),
        "real_pipeline_ran": real_ran,
        "detections_present": diag.get("detections_present"),
        "tracking_present": diag.get("tracking_present"),
        "sport_details_source": diag.get("sport_details_source"),
        "metadata_attempted": diag.get("metadata_attempted"),
        "metadata_status": diag.get("metadata_status"),
        "metadata_hint_source": _metadata_hint_source(response, clip.metadata_hints()),
        # decision output
        "verdict": actual_verdict,
        "confidence": actual_confidence,
        "cited_rule_id": cited_rule_id,
        "cited_rule": rule.get("section_title"),
        "status": "ok",
        "error": None,
    }
    if clip.expected_verdict is not None:
        record["expected_verdict"] = clip.expected_verdict
        record["verdict_matches_expected"] = (
            _normalize_verdict(actual_verdict) == _normalize_verdict(clip.expected_verdict)
        )
    if clip.expected_rule_id is not None:
        record["expected_rule_id"] = clip.expected_rule_id
        record["rule_matches_expected"] = bool(
            cited_rule_id and str(cited_rule_id).upper() == clip.expected_rule_id.upper()
        )
    if clip.expected_confidence is not None:
        record["confidence_meets_expectation"] = _confidence_meets_expectation(
            clip.expected_confidence, actual_confidence
        )
    return record


def _error_record(clip: DemoClip, message: str) -> dict:
    record = {
        "clip_id": clip.clip_id,
        "sport": clip.sport,
        "scenario": clip.scenario,
        "video_path": clip.video_path,
        "original_call": clip.original_call,
        "notes": clip.notes,
        "rule_citation": clip.rule_citation,
        "expected_confidence": clip.expected_confidence,
        "provider_used": None,
        "detector": None,
        "fallback_reason": message,
        "real_pipeline_ran": False,
        "detections_present": None,
        "tracking_present": None,
        "sport_details_source": None,
        "metadata_attempted": None,
        "metadata_status": None,
        "metadata_hint_source": "not_resolved",
        "verdict": None,
        "confidence": None,
        "cited_rule_id": None,
        "cited_rule": None,
        "status": "error",
        "error": message,
    }
    if clip.expected_verdict is not None:
        record["expected_verdict"] = clip.expected_verdict
        record["verdict_matches_expected"] = False
    if clip.expected_rule_id is not None:
        record["expected_rule_id"] = clip.expected_rule_id
        record["rule_matches_expected"] = False
    if clip.expected_confidence is not None:
        record["confidence_meets_expectation"] = None
    return record


def run_clip(clip: DemoClip, manifest_path: str | Path, provider: str | None, detector: str | None) -> dict:
    video = resolve_video_path(clip.video_path, manifest_path)
    try:
        response = run_demo(
            video,
            sport=clip.sport,
            provider=provider,
            detector=detector,
            metadata_hints=clip.metadata_hints(),
        )
    except FileNotFoundError as exc:
        return _error_record(clip, f"video file not found: {exc}")
    except Exception as exc:  # pragma: no cover - defensive; keep the suite going
        return _error_record(clip, f"{type(exc).__name__}: {exc}")
    return build_record(clip, response)


# ---------------------------------------------------------------------------
# Aggregate report
# ---------------------------------------------------------------------------

def _rate(matches: int, provided: int) -> float | None:
    """Match rate in [0, 1], or None when nothing was provided to compare."""
    return round(matches / provided, 3) if provided else None


def build_report(records: list[dict], *, provider: str | None, detector: str | None) -> dict:
    total = len(records)
    real = sum(1 for r in records if r.get("real_pipeline_ran"))
    metadata_resolved = sum(1 for r in records if r.get("metadata_status") == "resolved")
    errors = sum(1 for r in records if r.get("status") == "error")

    with_expected = [r for r in records if "verdict_matches_expected" in r]
    matched = sum(1 for r in with_expected if r["verdict_matches_expected"])
    with_rule = [r for r in records if "rule_matches_expected" in r]
    rule_matched = sum(1 for r in with_rule if r["rule_matches_expected"])
    with_conf = [r for r in records if r.get("confidence_meets_expectation") is not None]
    conf_met = sum(1 for r in with_conf if r["confidence_meets_expectation"])

    # Scenario coverage + verdict distribution + mean confidence (aggregate metrics).
    scenarios = sorted({r["scenario"] for r in records if r.get("scenario")})
    verdict_distribution: dict[str, int] = {"fair_call": 0, "bad_call": 0, "inconclusive": 0}
    for r in records:
        v = r.get("verdict")
        if v in verdict_distribution:
            verdict_distribution[v] += 1
    confidences = [r["confidence"] for r in records if isinstance(r.get("confidence"), (int, float))]
    average_confidence = round(sum(confidences) / len(confidences), 3) if confidences else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_requested": provider or "(env default)",
        "detector_requested": detector or "(env default)",
        "summary": {
            "total_clips": total,
            "real_pipeline_runs": real,
            "mock_or_fallback_runs": total - real,
            "metadata_resolved": metadata_resolved,
            "errors": errors,
            "expected_verdict_provided": len(with_expected),
            "expected_verdict_matches": matched,
            "verdict_accuracy": _rate(matched, len(with_expected)),
            "expected_rule_provided": len(with_rule),
            "rule_citation_matches": rule_matched,
            "rule_citation_accuracy": _rate(rule_matched, len(with_rule)),
            "confidence_expectation_provided": len(with_conf),
            "confidence_expectation_met": conf_met,
            "confidence_expectation_accuracy": _rate(conf_met, len(with_conf)),
            "scenarios_covered": scenarios,
            "scenario_count": len(scenarios),
            "verdict_distribution": verdict_distribution,
            "average_confidence": average_confidence,
        },
        "clips": records,
    }


def _fmt(value) -> str:
    return "—" if value in (None, "") else str(value)


def _pct(rate: float | None) -> str:
    return "—" if rate is None else f"{round(rate * 100)}%"


def _badge(flag) -> str:
    if flag is None:
        return "—"
    return "✅" if flag else "❌"


def render_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# RefCheck AI — Basketball Demo Suite Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Provider requested: `{report['provider_requested']}`  ·  Detector requested: `{report['detector_requested']}`",
        "",
        "## Summary",
        "",
        f"- **Total clips:** {s['total_clips']}  ·  **Scenarios covered:** {s['scenario_count']}",
        f"- **Real pipeline runs:** {s['real_pipeline_runs']}  ·  **Mock/fallback:** {s['mock_or_fallback_runs']}",
        f"- **Metadata resolved:** {s['metadata_resolved']} / {s['total_clips']}",
        f"- **Errors:** {s['errors']}",
        "",
        "### Aggregate metrics",
        "",
        "| Metric | Result |",
        "| --- | --- |",
        f"| Verdict accuracy | {s['expected_verdict_matches']} / {s['expected_verdict_provided']} ({_pct(s['verdict_accuracy'])}) |",
        f"| Rule-citation accuracy | {s['rule_citation_matches']} / {s['expected_rule_provided']} ({_pct(s['rule_citation_accuracy'])}) |",
        f"| Confidence-expectation met | {s['confidence_expectation_met']} / {s['confidence_expectation_provided']} ({_pct(s['confidence_expectation_accuracy'])}) |",
        f"| Average confidence | {_fmt(s['average_confidence'])} |",
        f"| Verdict distribution | fair_call {s['verdict_distribution']['fair_call']} · bad_call {s['verdict_distribution']['bad_call']} · inconclusive {s['verdict_distribution']['inconclusive']} |",
        "",
        f"_Scenarios:_ {', '.join(s['scenarios_covered']) or '—'}",
        "",
    ]
    if s["real_pipeline_runs"] == 0:
        lines += [
            "> ⚠️ **No clip ran the real pipeline in this environment.** Every clip fell back to "
            "mock (missing `ANTHROPIC_API_KEY` / `ffmpeg`, or placeholder media). See per-clip "
            "`fallback_reason` below.",
            "",
        ]

    # Results-at-a-glance table.
    lines += [
        "## Results",
        "",
        "| Clip | Scenario | Verdict | Conf | Expected | ✓ | Real |",
        "| --- | --- | --- | --- | --- | :-: | :-: |",
    ]
    for r in report["clips"]:
        verdict_match = _badge(r.get("verdict_matches_expected")) if "verdict_matches_expected" in r else "—"
        real = "✅" if r.get("real_pipeline_ran") else "mock"
        lines.append(
            f"| `{r['clip_id']}` | {_fmt(r.get('scenario'))} | `{_fmt(r.get('verdict'))}` | "
            f"{_fmt(r.get('confidence'))} | `{_fmt(r.get('expected_verdict'))}` | {verdict_match} | {real} |"
        )
    lines.append("")

    # Per-clip detail.
    lines += ["## Clips", ""]
    for r in report["clips"]:
        real = "✅ YES" if r.get("real_pipeline_ran") else "❌ NO"
        header = f"### {r['clip_id']}"
        if r.get("scenario"):
            header += f" — {r['scenario']}"
        lines += [
            header,
            "",
            f"- Original call: {_fmt(r.get('original_call'))}",
            f"- Real pipeline ran: **{real}**",
            f"- Verdict: `{_fmt(r.get('verdict'))}`  ·  Confidence: {_fmt(r.get('confidence'))}",
            f"- Cited rule: {_fmt(r.get('cited_rule_id'))} — {_fmt(r.get('cited_rule'))}",
        ]
        if r.get("rule_citation"):
            rule_badge = f"  → {_badge(r['rule_matches_expected'])}" if "rule_matches_expected" in r else ""
            lines.append(f"- Expected citation: {r['rule_citation']}{rule_badge}")
        if "verdict_matches_expected" in r:
            match = "✅ match" if r["verdict_matches_expected"] else "❌ mismatch"
            lines.append(f"- Expected verdict: `{_fmt(r.get('expected_verdict'))}` → {match}")
        if r.get("expected_confidence"):
            met = _badge(r.get("confidence_meets_expectation"))
            lines.append(f"- Expected confidence: `{r['expected_confidence']}` → {met}")
        lines.append(f"- Metadata: status=`{_fmt(r.get('metadata_status'))}` source=`{_fmt(r.get('metadata_hint_source'))}`")
        if r.get("fallback_reason"):
            lines.append(f"- Fallback reason: _{r['fallback_reason']}_")
        if r.get("notes"):
            lines.append(f"- Notes: {r['notes']}")
        lines.append("")
    return "\n".join(lines)


def print_console_summary(report: dict) -> None:
    s = report["summary"]
    print("================ DEMO SUITE ================")
    for r in report["clips"]:
        real = "REAL" if r.get("real_pipeline_ran") else "mock"
        expected = r.get("expected_verdict")
        mark = ""
        if "verdict_matches_expected" in r:
            mark = " ✓" if r["verdict_matches_expected"] else " ✗"
        print(
            f"  [{real:>4}] {_fmt(r.get('scenario')):<16} {r['clip_id']:<24} "
            f"verdict={_fmt(r.get('verdict')):<12} conf={_fmt(r.get('confidence')):<5} "
            f"exp={_fmt(expected)}{mark}"
        )
        if r.get("fallback_reason"):
            print(f"         ↳ fallback: {r['fallback_reason']}")
    print("--------------------------------------------")
    print(
        f"  clips={s['total_clips']} scenarios={s['scenario_count']} "
        f"real={s['real_pipeline_runs']} mock={s['mock_or_fallback_runs']} errors={s['errors']}"
    )
    print(
        f"  verdict_acc={s['expected_verdict_matches']}/{s['expected_verdict_provided']} ({_pct(s['verdict_accuracy'])}) "
        f"rule_acc={s['rule_citation_matches']}/{s['expected_rule_provided']} ({_pct(s['rule_citation_accuracy'])}) "
        f"conf_acc={s['confidence_expectation_met']}/{s['confidence_expectation_provided']} ({_pct(s['confidence_expectation_accuracy'])})"
    )
    print("============================================")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_demo_suite",
        description="Run a curated basketball demo suite and emit JSON + Markdown reports.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help=f"Path to the demo manifest JSON (default: {DEFAULT_MANIFEST}).",
    )
    parser.add_argument("--provider", choices=PROVIDERS, default=None, help="Override AI_PROVIDER.")
    parser.add_argument("--detector", choices=DETECTORS, default=None, help="Override DETECTOR.")
    parser.add_argument("--strict-real", action="store_true", help="Fail (nonzero) if any clip cannot run for real.")
    parser.add_argument("--output-json", default="demo_reports/demo_report.json", help="JSON report output path.")
    parser.add_argument("--output-md", default="demo_reports/demo_report.md", help="Markdown report output path.")
    parser.add_argument("--clip-id", default=None, help="Run only the manifest entry with this clip_id.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N clips.")
    return parser


def _write_report(report: dict, json_path: str | None, md_path: str | None) -> None:
    if json_path:
        out = Path(json_path).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str))
        print(f"JSON report → {out}")
    if md_path:
        out = Path(md_path).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(report))
        print(f"Markdown report → {out}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        clips = select_clips(load_manifest(args.manifest), args.clip_id, args.limit)
    except ManifestError as exc:
        print(f"Manifest error: {exc}", file=sys.stderr)
        return 2

    # Environment gate: mirror demo_analyze's strict-real behavior once, up front.
    # Use the first clip's resolved video for the readability line; the env-level
    # blockers (ffmpeg/key/ultralytics) are identical across clips.
    if args.strict_real:
        first_video = resolve_video_path(clips[0].video_path, args.manifest)
        checks = preflight(
            video_path=first_video,
            provider=args.provider,
            detector=args.detector,
            expect_metadata=any(c.sport.lower().strip() == "basketball" for c in clips),
        )
        env_blockers = [c for c in preflight_blockers(checks) if c.name != "input_video_readable"]
        if env_blockers:
            print(format_preflight(checks))
            sys.stdout.flush()
            print(
                "\nERROR: --strict-real requested but a REAL run is impossible.\n"
                "       Refusing to silently degrade to mock. Fix the blocking items above.",
                file=sys.stderr,
            )
            return 3

    records = [run_clip(clip, args.manifest, args.provider, args.detector) for clip in clips]
    report = build_report(records, provider=args.provider, detector=args.detector)

    print_console_summary(report)
    _write_report(report, args.output_json, args.output_md)

    if args.strict_real and any(not r.get("real_pipeline_ran") for r in records):
        print(
            "\nERROR: --strict-real requested but at least one clip fell back to mock. "
            "See fallback_reason in the report.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
