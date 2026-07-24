"""Provider benchmark runner — Claude vs Gemini vs mixed routing (Sprint 17D).

Compares the three deployment shapes the project ships across **accuracy, latency,
token usage, and estimated cost**, writing a Markdown + JSON comparison report.

Two modes:

- **Live** (`--live`): drives the real `analyze_clip` pipeline once per combo, so
  tokens/cost come from real provider calls (needs the relevant API keys; missing
  keys degrade to the mock fallback and record no tokens).
- **Estimate** (default): offline. Estimates each stage's token usage from the
  *real* prompt templates (perception + adjudicator system prompts + the injected
  rule corpus) for each clip's sport, routes those tokens to each combo's
  provider/model, and prices them at the list prices in `evaluation/cost.py`. This
  produces a reproducible cost/token comparison with no keys and no network. In
  estimate mode the verdict is a fixed placeholder, so the **accuracy columns are a
  baseline, not real model accuracy** — run `--live` with keys for that.

Usage:
    python scripts/benchmark_providers.py                        # estimate, basketball
    python scripts/benchmark_providers.py --dataset data/eval/benchmark_soccer.json
    python scripts/benchmark_providers.py --live                 # real pipeline (needs keys)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation.benchmark import resolve_combo, run_benchmark
from evaluation.report import render_html, render_markdown
from services import config
from services.ai import usage

DEFAULT_DATASET = "data/eval/benchmark_basketball.json"
DEFAULT_COMBOS = ["claude", "gemini", "mixed", "mock"]

# Representative completion sizes for the JSON replies each agent emits (tokens).
_PERCEPTION_COMPLETION = 220
_ADJUDICATION_COMPLETION = 260
_FRAMES = 10  # the pipeline samples 10 frames per clip


def _stage_prompt_tokens(sport: str) -> tuple[int, int]:
    """(perception_prompt_tokens, adjudication_prompt_tokens) from the real templates."""
    from services.analysis.prompts import _get_adjudicator_prompt, _get_perception_prompt
    from services.analysis.rule_corpus import _rule_records, _rules_text

    perception = _get_perception_prompt(sport)
    adjudicator = _get_adjudicator_prompt(sport)
    rules = _rules_text(list(_rule_records(sport)))
    perception_tokens = (
        usage.estimate_tokens(perception)
        + _FRAMES * usage.IMAGE_TOKEN_ESTIMATE
        + usage.estimate_tokens("The on-court referee called: ...")
    )
    # Adjudicators see the prompt + full rule corpus + the perception JSON payload.
    adjudication_tokens = (
        usage.estimate_tokens(adjudicator) + usage.estimate_tokens(rules) + _PERCEPTION_COMPLETION
    )
    return perception_tokens, adjudication_tokens


def _routing_from_env() -> tuple[tuple[str, str], tuple[str, str]]:
    """Resolve (perception provider, model) and (adjudication provider, model) from env.

    Mirrors how the router resolves each stage, so the estimate matches the combo.
    """
    provider = os.environ.get("AI_PROVIDER", "mock")
    if provider == "router":
        p_provider = config.router_provider_for(config.TASK_PERCEPTION)
        a_provider = config.router_provider_for(config.TASK_ADJUDICATION)
        p_model = config.router_model_for(config.TASK_PERCEPTION) or config.resolved_model_for_provider(p_provider)
        a_model = config.router_model_for(config.TASK_ADJUDICATION) or config.resolved_model_for_provider(a_provider)
    else:
        p_provider = a_provider = provider
        p_model = a_model = config.resolved_model_for_provider(provider)
    return (p_provider, p_model or provider), (a_provider, a_model or provider)


def _make_estimate_analyze_fn():
    def analyze(**kwargs) -> dict:
        sport = kwargs.get("sport") or "basketball"
        provider = os.environ.get("AI_PROVIDER", "mock")
        if provider != "mock":  # mock is offline/free — records nothing
            perception_prompt_tokens, adjudication_prompt_tokens = _stage_prompt_tokens(sport)
            (p_provider, p_model), (a_provider, a_model) = _routing_from_env()
            # 1 perception call + 2 adjudicators (conservative ∥ skeptical).
            usage.record(p_provider, p_model, perception_prompt_tokens, _PERCEPTION_COMPLETION)
            for _ in range(2):
                usage.record(a_provider, a_model, adjudication_prompt_tokens, _ADJUDICATION_COMPLETION)
        return {"clip_id": "estimate", "verdict": {"verdict": "fair_call", "confidence": 0.5}}

    return analyze


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="benchmark_providers", description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Labeled dataset JSON.")
    parser.add_argument(
        "--combos", default=",".join(DEFAULT_COMBOS),
        help="Comma-separated combos: claude,gemini,mixed,mock (default: all four).",
    )
    parser.add_argument("--live", action="store_true", help="Drive the real pipeline (needs API keys).")
    parser.add_argument("--md", default=None, help="Markdown output path (default: alongside JSON).")
    parser.add_argument("--json", dest="json_out", default=None, help="JSON output path.")
    parser.add_argument("--html", default=None, help="Optional HTML output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    combos = [c.strip() for c in args.combos.split(",") if c.strip()]
    for name in combos:
        resolve_combo(name)  # validate early with a clear error

    analyze_fn = None if args.live else _make_estimate_analyze_fn()
    report = run_benchmark(args.dataset, combos, analyze_fn=analyze_fn)

    stem = Path(args.dataset).stem.replace("benchmark_", "")
    default_dir = Path("evaluation/reports")
    json_out = Path(args.json_out) if args.json_out else default_dir / f"provider_benchmark_{stem}.json"
    md_out = Path(args.md) if args.md else default_dir / f"provider_benchmark_{stem}.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report.to_dict(), indent=2))
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(render_markdown(report))
    if args.html:
        Path(args.html).write_text(render_html(report))

    mode = "live" if args.live else "estimate"
    print(f"[{mode}] benchmarked {len(combos)} combo(s) over {report.clip_count} clips")
    for r in report.results:
        print(
            f"  {r.provider:>7} | acc={r.evaluation.accuracy:.3f} "
            f"mean_ms={r.latency.mean_ms:.1f} tokens={r.usage.total_tokens} "
            f"est_cost=${r.cost.total_usd:.4f}"
        )
    print(f"  recommended={report.recommended_provider()}  cheapest={report.cheapest_provider()}")
    print(f"Wrote {md_out} and {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
