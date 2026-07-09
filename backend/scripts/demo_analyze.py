"""Run a local video clip through the real RefCheck analysis pipeline and print a
compact "what actually ran" report.

This is a demo/observability helper — it calls the same `analyze_clip` the API
uses, so the diagnostics it prints reflect the true runtime path.

Examples (run from the `backend/` directory):

    # Default (mock unless AI_PROVIDER=anthropic is set): proves the plumbing
    python scripts/demo_analyze.py --video ~/Downloads/NBA_GAME.mp4

    # Real Claude-vision path (needs ANTHROPIC_API_KEY + ffmpeg installed):
    python scripts/demo_analyze.py --video clip.mp4 --provider anthropic --detector claude_vision

    # Real tracked-detection path (needs ultralytics + ffmpeg + key):
    python scripts/demo_analyze.py --video clip.mp4 --provider anthropic --detector hybrid --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

# Allow running directly (python scripts/demo_analyze.py) from backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PROVIDERS = ("mock", "anthropic")
DETECTORS = ("claude_vision", "yolov8", "hybrid")


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
) -> dict:
    """Analyze one local clip through the real pipeline and return the response."""
    path = Path(video_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Clip not found: {path}")

    video_metadata = {
        "filename": path.name,
        "content_type": "video/mp4",
        "size_bytes": path.stat().st_size,
        "stored_path": str(path.resolve()),
    }
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


def format_report(response: dict) -> str:
    """Human-readable 'what actually ran' summary from the response."""
    verdict = response.get("verdict", {}) or {}
    diag = response.get("diagnostics", {}) or {}
    rule = verdict.get("cited_rule", {}) or {}
    game = response.get("game_context")

    lines = [
        "================ WHAT ACTUALLY RAN ================",
        f"provider_used        : {diag.get('provider_used')}",
        f"detector             : {diag.get('detector')}",
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
        "------------------ VERDICT ------------------------",
        f"verdict              : {verdict.get('verdict')}  ({verdict.get('confidence')})",
        f"cited_rule           : {rule.get('rule_id')} — {rule.get('section_title')}",
        f"reasoning            : {(verdict.get('reasoning') or '')[:160]}",
    ]
    if game:
        lines += [
            "------------------ GAME CONTEXT -------------------",
            f"resolution_status    : {game.get('resolution_status')}",
            f"matchup              : {game.get('away_team')} @ {game.get('home_team')}",
            f"game_date/season     : {game.get('game_date')} / {game.get('season')}",
        ]
    is_real = diag.get("provider_used") == "anthropic_four_agent" and not diag.get("fallback_reason")
    lines.append("===================================================")
    lines.append(f"REAL pipeline ran (not mock/fallback): {is_real}")
    return "\n".join(lines)


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        response = run_demo(args.video, sport=args.sport, provider=args.provider, detector=args.detector)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(format_report(response))
    if args.json:
        print(json.dumps(response, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
