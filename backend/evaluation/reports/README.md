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
