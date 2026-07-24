# RefCheck AI — Evaluation Benchmark

- Dataset: `data/eval/benchmark_hockey.json`  ·  Detector: `claude_vision`  ·  Clips: 7
- Generated: `2026-07-24T20:14:10.572478+00:00`

## Provider comparison

| Provider | Accuracy | Macro F1 | Kappa | ECE | MCC | Brier | Mean latency (ms) | p95 (ms) | Tokens | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| claude | 57% | 0.242 | 0.000 | 0.071 | 0.000 | 0.250 | 0.594 | 2.745 | 105,315 | $0.3781 |
| gemini | 57% | 0.242 | 0.000 | 0.071 | 0.000 | 0.250 | 0.036 | 0.046 | 105,315 | $0.0430 |
| mixed | 57% | 0.242 | 0.000 | 0.071 | 0.000 | 0.250 | 0.038 | 0.049 | 105,315 | $0.1481 |
| mock ★ | 57% | 0.242 | 0.000 | 0.071 | 0.000 | 0.250 | 0.014 | 0.018 | — | — |

**Recommended provider: `mock`** ★ — highest accuracy, then Matthews correlation, then best-calibrated (lowest Brier), then fastest.

**Lowest estimated cost: `gemini`** 💲 — token counts are estimates and prices are list (see `evaluation/cost.py`); use for relative comparison.

## Provider: claude

- Clips: 7  ·  Accuracy: 57%  ·  Macro P/R/F1: 0.190 / 0.333 / 0.242
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.071  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.594 · p50 0.039 · p95 2.745 · max 3.888
- Tokens (estimated): 105,315 (prompt 100,135 · completion 5,180; 21 call(s))  ·  Est. cost: $0.3781

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 2 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.571 | 1.000 | 0.727 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 2 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 7 | 0.500 | 0.571 |

## Provider: gemini

- Clips: 7  ·  Accuracy: 57%  ·  Macro P/R/F1: 0.190 / 0.333 / 0.242
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.071  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.036 · p50 0.033 · p95 0.046 · max 0.049
- Tokens (estimated): 105,315 (prompt 100,135 · completion 5,180; 21 call(s))  ·  Est. cost: $0.0430

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 2 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.571 | 1.000 | 0.727 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 2 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 7 | 0.500 | 0.571 |

## Provider: mixed

- Clips: 7  ·  Accuracy: 57%  ·  Macro P/R/F1: 0.190 / 0.333 / 0.242
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.071  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.038 · p50 0.035 · p95 0.049 · max 0.053
- Tokens (estimated): 105,315 (prompt 100,135 · completion 5,180; 21 call(s))  ·  Est. cost: $0.1481  ·  by model — gemini-2.5-flash: 79,611 tok / $0.0273; claude-sonnet-4-5: 25,704 tok / $0.1208

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 2 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.571 | 1.000 | 0.727 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 2 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 7 | 0.500 | 0.571 |

## Provider: mock

- Clips: 7  ·  Accuracy: 57%  ·  Macro P/R/F1: 0.190 / 0.333 / 0.242
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.071  ·  Brier: 0.250  ·  Mean confidence: 0.500
- Latency ms — mean 0.014 · p50 0.013 · p95 0.018 · max 0.019
- Tokens (estimated): — (prompt — · completion —; 0 call(s))  ·  Est. cost: —

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 4 | 0 | 0 |
| bad_call | 2 | 0 | 0 |
| inconclusive | 1 | 0 | 0 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.571 | 1.000 | 0.727 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 2 |
| inconclusive | 0.000 | 0.000 | 0.000 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.5–0.6 | 7 | 0.500 | 0.571 |
