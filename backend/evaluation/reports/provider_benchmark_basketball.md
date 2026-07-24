# RefCheck AI — Evaluation Benchmark

- Dataset: `data/eval/benchmark_basketball.json`  ·  Detector: `claude_vision`  ·  Clips: 10
- Generated: `2026-07-24T20:14:10.336668+00:00`

## Provider comparison

| Provider | Accuracy | Macro F1 | Kappa | ECE | MCC | Brier | Mean latency (ms) | p95 (ms) | Tokens | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| claude | 50% | 0.222 | 0.000 | 0.000 | 0.000 | 0.250 | 0.682 | 3.589 | 147,340 | $0.5308 |
| gemini | 50% | 0.222 | 0.000 | 0.000 | 0.000 | 0.250 | 0.033 | 0.044 | 147,340 | $0.0605 |
| mixed | 50% | 0.222 | 0.000 | 0.000 | 0.000 | 0.250 | 0.035 | 0.047 | 147,340 | $0.2004 |
| mock ★ | 50% | 0.222 | 0.000 | 0.000 | 0.000 | 0.250 | 0.014 | 0.018 | — | — |

**Recommended provider: `mock`** ★ — highest accuracy, then Matthews correlation, then best-calibrated (lowest Brier), then fastest.

**Lowest estimated cost: `gemini`** 💲 — token counts are estimates and prices are list (see `evaluation/cost.py`); use for relative comparison.

## Provider: claude

- Clips: 10  ·  Accuracy: 50%  ·  Macro P/R/F1: 0.167 / 0.333 / 0.222
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.000  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.682 · p50 0.033 · p95 3.589 · max 6.470
- Tokens (estimated): 147,340 (prompt 139,940 · completion 7,400; 30 call(s))  ·  Est. cost: $0.5308

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 5 | 0 | 0 |
| bad_call | 3 | 0 | 0 |
| inconclusive | 2 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.500 | 1.000 | 0.667 | 5 |
| bad_call | 0.000 | 0.000 | 0.000 | 3 |
| inconclusive | 0.000 | 0.000 | 0.000 | 2 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 10 | 0.500 | 0.500 |

## Provider: gemini

- Clips: 10  ·  Accuracy: 50%  ·  Macro P/R/F1: 0.167 / 0.333 / 0.222
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.000  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.033 · p50 0.031 · p95 0.044 · max 0.050
- Tokens (estimated): 147,340 (prompt 139,940 · completion 7,400; 30 call(s))  ·  Est. cost: $0.0605

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 5 | 0 | 0 |
| bad_call | 3 | 0 | 0 |
| inconclusive | 2 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.500 | 1.000 | 0.667 | 5 |
| bad_call | 0.000 | 0.000 | 0.000 | 3 |
| inconclusive | 0.000 | 0.000 | 0.000 | 2 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 10 | 0.500 | 0.500 |

## Provider: mixed

- Clips: 10  ·  Accuracy: 50%  ·  Macro P/R/F1: 0.167 / 0.333 / 0.222
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.000  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.035 · p50 0.032 · p95 0.047 · max 0.052
- Tokens (estimated): 147,340 (prompt 139,940 · completion 7,400; 30 call(s))  ·  Est. cost: $0.2004  ·  by model — gemini-2.5-flash: 114,400 tok / $0.0392; claude-sonnet-4-5: 32,940 tok / $0.1612

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 5 | 0 | 0 |
| bad_call | 3 | 0 | 0 |
| inconclusive | 2 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.500 | 1.000 | 0.667 | 5 |
| bad_call | 0.000 | 0.000 | 0.000 | 3 |
| inconclusive | 0.000 | 0.000 | 0.000 | 2 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 10 | 0.500 | 0.500 |

## Provider: mock

- Clips: 10  ·  Accuracy: 50%  ·  Macro P/R/F1: 0.167 / 0.333 / 0.222
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.000  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.014 · p50 0.013 · p95 0.018 · max 0.020
- Tokens (estimated): — (prompt — · completion —; 0 call(s))  ·  Est. cost: —

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 5 | 0 | 0 |
| bad_call | 3 | 0 | 0 |
| inconclusive | 2 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.500 | 1.000 | 0.667 | 5 |
| bad_call | 0.000 | 0.000 | 0.000 | 3 |
| inconclusive | 0.000 | 0.000 | 0.000 | 2 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 10 | 0.500 | 0.500 |
