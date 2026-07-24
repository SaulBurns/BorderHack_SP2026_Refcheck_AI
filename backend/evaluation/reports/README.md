# Benchmark reports (Sprint 14)

Committed, reproducible benchmark artifacts — one per sport dataset — produced by
the evaluation harness. Each `benchmark_<sport>.md` (+ `.json`) tabulates the
provider comparison with the Sprint 14 metrics: accuracy, macro-F1, Cohen's kappa,
**MCC** (Matthews correlation), ECE, **Brier score** (confidence calibration), and
latency, plus a **recommended provider** picked by accuracy → MCC → calibration →
speed.

Regenerate them offline (no API keys needed — the real/absent providers degrade to
the mock fallback, which is labeled honestly):

```bash
cd backend
for s in basketball soccer hockey lacrosse; do
  python -m evaluation --dataset data/eval/benchmark_$s.json \
    --providers mock,anthropic,gemini \
    --output evaluation/reports/benchmark_$s.json \
    --md evaluation/reports/benchmark_$s.md
done
```

For a **real** provider comparison, set `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` and
run the same command — the harness then drives each provider's live pipeline and
the numbers diverge. The `generated_at` timestamp changes on every run; that is the
only churn when re-committing.

## Provider benchmark — cost & tokens (Sprint 17D)

`provider_benchmark_<sport>.md` (+ `.json`) compare the three deployment shapes the
project ships — **`claude`** (Anthropic), **`gemini`** (Google), and **`mixed`**
(the Sprint 17B router: perception→Gemini, adjudication→Claude) — plus the free
**`mock`** baseline, across **accuracy, latency, token usage, and estimated cost**.
They are produced by `scripts/benchmark_providers.py`:

```bash
cd backend
for s in basketball soccer hockey lacrosse; do
  python scripts/benchmark_providers.py --dataset data/eval/benchmark_$s.json
done
```

By default the runner is **offline (estimate mode)**: it estimates each stage's
token usage from the *real* prompt templates (perception + adjudicator system
prompts + the injected rule corpus), routes those tokens to each combo's
provider/model, and prices them at the list prices in `evaluation/cost.py`. This
yields a reproducible **cost/token** comparison with no keys — the headline result
(e.g. Gemini ≈ 9× cheaper than Claude for the same prompts; mixed lands in
between). Two honesty caveats, both stated in the report:

- **Token counts are estimates** and **prices are list**, not negotiated — use the
  numbers for *relative* comparison, not billing.
- In estimate mode the verdict is a fixed placeholder, so the **accuracy / metric
  columns are an offline baseline, identical across combos — not real model
  accuracy** (hence the `recommended_provider` is not meaningful offline; the
  `cheapest_provider` callout is). Run with `--live` **and** the API keys for a
  real accuracy + cost comparison.
