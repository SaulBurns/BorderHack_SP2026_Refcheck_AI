# RefCheck AI — Evaluation Benchmark

- Dataset: `data/eval/benchmark_lacrosse.json`  ·  Detector: `claude_vision`  ·  Clips: 6
- Generated: `2026-07-24T20:14:10.691017+00:00`

## Provider comparison

| Provider | Accuracy | Macro F1 | Kappa | ECE | MCC | Brier | Mean latency (ms) | p95 (ms) | Tokens | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| claude | 67% | 0.267 | 0.000 | 0.167 | 0.000 | 0.250 | 0.675 | 2.886 | 89,208 | $0.3209 |
| gemini | 67% | 0.267 | 0.000 | 0.167 | 0.000 | 0.250 | 0.038 | 0.047 | 89,208 | $0.0365 |
| mixed | 67% | 0.267 | 0.000 | 0.167 | 0.000 | 0.250 | 0.040 | 0.051 | 89,208 | $0.1235 |
| mock ★ | 67% | 0.267 | 0.000 | 0.167 | 0.000 | 0.250 | 0.016 | 0.019 | — | — |

**Recommended provider: `mock`** ★ — highest accuracy, then Matthews correlation, then best-calibrated (lowest Brier), then fastest.

**Lowest estimated cost: `gemini`** 💲 — token counts are estimates and prices are list (see `evaluation/cost.py`); use for relative comparison.

## Provider: claude

- Clips: 6  ·  Accuracy: 67%  ·  Macro P/R/F1: 0.222 / 0.333 / 0.267
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.167  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.675 · p50 0.043 · p95 2.886 · max 3.826
- Tokens (estimated): 89,208 (prompt 84,768 · completion 4,440; 18 call(s))  ·  Est. cost: $0.3209

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 1 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.667 | 1.000 | 0.800 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 1 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 6 | 0.500 | 0.667 |

## Provider: gemini

- Clips: 6  ·  Accuracy: 67%  ·  Macro P/R/F1: 0.222 / 0.333 / 0.267
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.167  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.038 · p50 0.037 · p95 0.047 · max 0.049
- Tokens (estimated): 89,208 (prompt 84,768 · completion 4,440; 18 call(s))  ·  Est. cost: $0.0365

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 1 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.667 | 1.000 | 0.800 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 1 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 6 | 0.500 | 0.667 |

## Provider: mixed

- Clips: 6  ·  Accuracy: 67%  ·  Macro P/R/F1: 0.222 / 0.333 / 0.267
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.167  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.040 · p50 0.037 · p95 0.051 · max 0.054
- Tokens (estimated): 89,208 (prompt 84,768 · completion 4,440; 18 call(s))  ·  Est. cost: $0.1235  ·  by model — gemini-2.5-flash: 68,304 tok / $0.0234; claude-sonnet-4-5: 20,904 tok / $0.1002

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 1 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.667 | 1.000 | 0.800 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 1 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 6 | 0.500 | 0.667 |

## Provider: mock

- Clips: 6  ·  Accuracy: 67%  ·  Macro P/R/F1: 0.222 / 0.333 / 0.267
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.167  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.016 · p50 0.015 · p95 0.019 · max 0.020
- Tokens (estimated): — (prompt — · completion —; 0 call(s))  ·  Est. cost: —

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 1 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.667 | 1.000 | 0.800 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 1 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 6 | 0.500 | 0.667 |
