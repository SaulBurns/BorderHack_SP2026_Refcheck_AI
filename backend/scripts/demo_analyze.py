"""Run a local video clip through the real RefCheck analysis pipeline and print a
compact "what actually ran" report — with an environment preflight so you can tell,
before and after the run, whether a REAL pipeline path is even possible.

This is a demo/observability helper — it calls the same `analyze_clip` the API
uses, so the diagnostics it prints reflect the true runtime path.

Examples (run from the `backend/` directory):

    # Preflight only: check the environment without analyzing anything.
    python scripts/demo_analyze.py --video clip.mp4 --provider anthropic --preflight-only

    # Default (mock unless AI_PROVIDER=anthropic): proves the plumbing.
    python scripts/demo_analyze.py --video ~/Downloads/NBA_GAME.mp4

    # Real Claude-vision path (needs ANTHROPIC_API_KEY + ffmpeg installed):
    python scripts/demo_analyze.py --video clip.mp4 --provider anthropic --detector claude_vision

    # Fail loudly if a REAL run is impossible instead of silently degrading to mock:
    python scripts/demo_analyze.py --video clip.mp4 --provider anthropic --detector hybrid --strict-real

    # Demo NBA metadata resolution without renaming the file:
    python scripts/demo_analyze.py --video NBA_GAME.mp4 --provider anthropic \
        --game-date 2024-12-25 --home-team LAL --away-team BOS
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

# Allow running directly (python scripts/demo_analyze.py) from backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import config  # noqa: E402  (after sys.path bootstrap)

PROVIDERS = ("mock", "anthropic")
DETECTORS = ("claude_vision", "yolov8", "hybrid")
YOLO_DETECTORS = ("yolov8", "hybrid")


# ---------------------------------------------------------------------------
# Preflight — is a REAL run of the requested configuration possible?
# ---------------------------------------------------------------------------

class PreflightCheck(SimpleNamespace):
    """A single named requirement with pass/fail and actionable guidance."""


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def preflight(
    *,
    video_path: str | Path,
    provider: str | None,
    detector: str | None,
    expect_metadata: bool = True,
) -> list[PreflightCheck]:
    """Validate the runtime environment for a real run of this configuration.

    `provider`/`detector` are the *requested* values (None means "inherit env").
    Returns an ordered list of checks; a check is `critical` when its failure
    makes a real run impossible.
    """
    resolved_provider = config.resolved_provider(provider)
    resolved_detector = config.resolved_detector(detector)
    wants_anthropic = resolved_provider == "anthropic"
    wants_yolo = resolved_detector in YOLO_DETECTORS

    checks: list[PreflightCheck] = []

    # Input video file.
    path = Path(video_path).expanduser()
    file_ok = path.is_file() and os.access(path, os.R_OK)
    checks.append(PreflightCheck(
        name="input_video_readable",
        passed=file_ok,
        critical=True,
        detail=str(path) if file_ok else f"cannot read video file: {path}",
        remedy="Pass a path to a readable local video via --video.",
    ))

    # ffmpeg — required for frame extraction on any real run.
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    checks.append(PreflightCheck(
        name="ffmpeg",
        passed=ffmpeg_ok,
        # Only strictly required when we actually intend a real (anthropic) run.
        critical=wants_anthropic,
        detail="found" if ffmpeg_ok else "ffmpeg not on PATH",
        remedy="Install ffmpeg (e.g. `brew install ffmpeg`).",
    ))

    # ffprobe — used by the extraction path to read duration; nice-to-have.
    ffprobe_ok = shutil.which("ffprobe") is not None
    checks.append(PreflightCheck(
        name="ffprobe",
        passed=ffprobe_ok,
        critical=False,
        detail="found" if ffprobe_ok else "ffprobe not on PATH (duration probing degrades gracefully)",
        remedy="Install ffmpeg, which bundles ffprobe.",
    ))

    # ANTHROPIC_API_KEY — required when provider is anthropic.
    key_present = bool((os.getenv("ANTHROPIC_API_KEY") or "").strip())
    checks.append(PreflightCheck(
        name="anthropic_api_key",
        passed=key_present or not wants_anthropic,
        critical=wants_anthropic,
        detail="set" if key_present else ("not required for provider=mock" if not wants_anthropic else "ANTHROPIC_API_KEY is not set"),
        remedy="export ANTHROPIC_API_KEY=sk-ant-...",
    ))

    # ultralytics — required for YOLO-based detectors.
    ultra_ok = _module_available("ultralytics")
    checks.append(PreflightCheck(
        name="ultralytics",
        passed=ultra_ok or not wants_yolo,
        critical=wants_yolo,
        detail="importable" if ultra_ok else (f"not needed for detector={resolved_detector}" if not wants_yolo else "ultralytics is not importable"),
        remedy="pip install ultralytics",
    ))

    # nba_api — needed for basketball metadata resolution (never critical:
    # metadata enrichment is additive and degrades gracefully).
    nba_ok = _module_available("nba_api")
    checks.append(PreflightCheck(
        name="nba_api",
        passed=nba_ok or not expect_metadata,
        critical=False,
        detail="importable" if nba_ok else "nba_api not importable (metadata will be unresolved/unavailable)",
        remedy="pip install nba_api",
    ))

    return checks


def preflight_blockers(checks: list[PreflightCheck]) -> list[PreflightCheck]:
    """Critical checks that failed — a real run is impossible while any exist."""
    return [c for c in checks if c.critical and not c.passed]


def format_preflight(checks: list[PreflightCheck]) -> str:
    blockers = preflight_blockers(checks)
    lines = ["=== PREFLIGHT ==="]
    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        flag = "  (blocks real run)" if c.critical and not c.passed else ""
        lines.append(f"  [{status}] {c.name:<20} {c.detail}{flag}")
    if blockers:
        lines.append("  A REAL run is NOT possible. Fix the blocking items above:")
        for c in blockers:
            lines.append(f"    - {c.name}: {c.remedy}")
    else:
        lines.append("  Real-run prerequisites satisfied for the requested configuration.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def _restore_env(key: str, previous: str | None) -> None:
    if previous is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = previous


def run_demo(
    video_path: str | Path,
    sport: str = "basketball",
    provider: str | None = None,
    detector: str | None = None,
    metadata_hints: dict | None = None,
) -> dict:
    """Analyze one local clip through the real pipeline and return the response.

    `metadata_hints` are threaded through the existing `video_metadata` dict, so
    no API contract or `analyze_clip` signature changes are required.
    """
    path = Path(video_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Clip not found: {path}")

    video_metadata = {
        "filename": path.name,
        "content_type": "video/mp4",
        "size_bytes": path.stat().st_size,
        "stored_path": str(path.resolve()),
    }
    if metadata_hints:
        # Only carry keys with actual values; empty flags stay out of the dict.
        video_metadata.update({k: v for k, v in metadata_hints.items() if v})
    # The pipeline only reads .filename / .content_type off the file (mock path).
    file_stub = SimpleNamespace(filename=path.name, content_type="video/mp4")

    prev_provider = os.environ.get("AI_PROVIDER")
    prev_detector = os.environ.get("DETECTOR")
    if provider is not None:
        os.environ["AI_PROVIDER"] = provider
    if detector is not None:
        os.environ["DETECTOR"] = detector
    try:
        from services.ai_analyzer import analyze_clip

        return analyze_clip(file=file_stub, sport=sport, video_metadata=video_metadata)
    finally:
        _restore_env("AI_PROVIDER", prev_provider)
        _restore_env("DETECTOR", prev_detector)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _real_pipeline_ran(diag: dict) -> bool:
    """Strict definition: a real provider ran with no fallback.

    Detector is intentionally NOT part of this test — claude_vision is a valid
    real detector, so requiring YOLO would falsely mark good real runs as fake.
    """
    return diag.get("provider_used") == "anthropic_four_agent" and not diag.get("fallback_reason")


def _metadata_hint_source(response: dict, metadata_hints: dict | None) -> str:
    """Where did the resolved game context come from: explicit hints, filename, or nothing."""
    game = response.get("game_context") or {}
    status = game.get("resolution_status")
    if status in (None, "skipped", "unresolved"):
        return "not_resolved"
    reasons = " ".join(game.get("match_reasons") or [])
    used_hints = bool(metadata_hints and any(metadata_hints.values()))
    if used_hints and ("hint" in reasons):
        return "explicit_demo_hints"
    if "filename" in reasons:
        return "filename_parsing"
    return "explicit_demo_hints" if used_hints else "filename_parsing"


def format_report(
    response: dict,
    *,
    provider_requested: str | None = None,
    detector_requested: str | None = None,
    metadata_hints: dict | None = None,
) -> str:
    """Human-readable 'what actually ran' summary from the response."""
    verdict = response.get("verdict", {}) or {}
    diag = response.get("diagnostics", {}) or {}
    rule = verdict.get("cited_rule", {}) or {}
    game = response.get("game_context")
    is_real = _real_pipeline_ran(diag)

    lines = [
        "================ WHAT ACTUALLY RAN ================",
        f"provider_requested   : {provider_requested or '(env default)'}",
        f"provider_used        : {diag.get('provider_used')}",
        f"detector_requested   : {detector_requested or '(env default)'}",
        f"detector_used        : {diag.get('detector')}",
        f"fallback_reason      : {diag.get('fallback_reason')}",
        f"frames_analyzed      : {diag.get('frames_analyzed')}",
        f"detections_present   : {diag.get('detections_present')}",
        f"tracking_present     : {diag.get('tracking_present')}",
        f"tracked_object_count : {diag.get('tracked_object_count')}",
        f"player_count         : {diag.get('player_count')}",
        f"ball_present         : {diag.get('ball_present')}",
        f"sport_details_source : {diag.get('sport_details_source')}",
        f"metadata_attempted   : {diag.get('metadata_attempted')}",
        f"metadata_status      : {diag.get('metadata_status')}",
        f"metadata_hint_source : {_metadata_hint_source(response, metadata_hints)}",
        f"game_context_present : {game is not None}",
        "------------------ VERDICT ------------------------",
        f"verdict              : {verdict.get('verdict')}",
        f"confidence           : {verdict.get('confidence')}",
        f"cited_rule_id        : {rule.get('rule_id')}",
        f"cited_rule           : {rule.get('section_title')}",
        f"reasoning            : {(verdict.get('reasoning') or '')[:160]}",
    ]
    if game:
        lines += [
            "------------------ GAME CONTEXT -------------------",
            f"resolution_status    : {game.get('resolution_status')}",
            f"matchup              : {game.get('away_team')} @ {game.get('home_team')}",
            f"game_date/season     : {game.get('game_date')} / {game.get('season')}",
        ]
    lines.append("===================================================")
    if is_real:
        lines.append("REAL PIPELINE RAN: YES")
    else:
        lines.append("REAL PIPELINE RAN: NO")
        lines.append("  >>> FELL BACK TO MOCK <<<")
        lines.append(f"  reason: {diag.get('fallback_reason') or 'provider_used=' + str(diag.get('provider_used'))}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demo_analyze",
        description="Run a local clip through the real RefCheck pipeline and show what ran.",
    )
    parser.add_argument("--video", required=True, help="Path to a local video clip.")
    parser.add_argument("--sport", default="basketball")
    parser.add_argument("--provider", choices=PROVIDERS, default=None, help="Override AI_PROVIDER.")
    parser.add_argument("--detector", choices=DETECTORS, default=None, help="Override DETECTOR.")
    parser.add_argument("--json", action="store_true", help="Also print the full JSON response.")
    parser.add_argument(
        "--strict-real",
        action="store_true",
        help="Exit nonzero if a real run is impossible instead of degrading to mock.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run the environment preflight and exit without analyzing.",
    )
    parser.add_argument("--game-date", default=None, help="Explicit game date hint (YYYY-MM-DD).")
    parser.add_argument("--home-team", default=None, help="Explicit home team hint (e.g. LAL or Lakers).")
    parser.add_argument("--away-team", default=None, help="Explicit away team hint (e.g. BOS or Celtics).")
    return parser


def _metadata_hints_from_args(args: argparse.Namespace) -> dict:
    return {
        "clip_date_hint": args.game_date,
        "home_team_hint": args.home_team,
        "away_team_hint": args.away_team,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata_hints = _metadata_hints_from_args(args)
    expect_metadata = args.sport.lower().strip() == "basketball"

    checks = preflight(
        video_path=args.video,
        provider=args.provider,
        detector=args.detector,
        expect_metadata=expect_metadata,
    )
    print(format_preflight(checks))
    sys.stdout.flush()  # keep stdout/stderr ordering sane when piped together
    blockers = preflight_blockers(checks)

    if args.strict_real and blockers:
        print(
            "\nERROR: --strict-real was requested but a REAL run is impossible.\n"
            "       Refusing to silently degrade to mock. Fix the blocking items above.",
            file=sys.stderr,
        )
        return 3

    if args.preflight_only:
        return 1 if blockers else 0

    try:
        response = run_demo(
            args.video,
            sport=args.sport,
            provider=args.provider,
            detector=args.detector,
            metadata_hints=metadata_hints,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print()
    print(format_report(
        response,
        provider_requested=args.provider,
        detector_requested=args.detector,
        metadata_hints=metadata_hints,
    ))
    if args.json:
        print(json.dumps(response, indent=2, default=str))

    # In strict mode, a run that still ended up on the mock path is a failure.
    if args.strict_real and not _real_pipeline_ran(response.get("diagnostics", {}) or {}):
        print(
            "\nERROR: --strict-real requested but the pipeline fell back to mock.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
