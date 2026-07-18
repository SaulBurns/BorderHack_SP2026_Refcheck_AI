# RefCheck AI — Evaluation Benchmark

- Dataset: `data/eval/benchmark_basketball.json`  ·  Detector: `claude_vision`  ·  Clips: 10
- Generated: `2026-07-18T02:59:43.243660+00:00`

## Provider comparison

| Provider | Accuracy | Macro F1 | Kappa | ECE | MCC | Brier | Mean latency (ms) | p95 (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mock | 30% | 0.259 | 0.067 | 0.199 | 0.094 | 0.232 | 860.480 | 1400.037 |
| anthropic ★ | 30% | 0.259 | 0.067 | 0.199 | 0.094 | 0.232 | 88.358 | 97.856 |
| gemini | 30% | 0.259 | 0.067 | 0.199 | 0.094 | 0.232 | 86.483 | 87.325 |

**Recommended provider: `anthropic`** ★ — highest accuracy, then Matthews correlation, then best-calibrated (lowest Brier), then fastest.

## Provider: mock

- Clips: 10  ·  Accuracy: 30%  ·  Macro P/R/F1: 0.429 / 0.400 / 0.259
- Cohen's kappa: 0.067  ·  MCC: 0.094  ·  ECE: 0.199  ·  Brier: 0.232  ·  Mean confidence: 0.461
- Latency ms — mean 860.480 · p50 741.024 · p95 1400.037 · max 1632.766

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 1 | 2 | 2 |
| bad_call | 0 | 0 | 3 |
| inconclusive | 0 | 0 | 2 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 1.000 | 0.200 | 0.333 | 5 |
| bad_call | 0.000 | 0.000 | 0.000 | 3 |
| inconclusive | 0.286 | 1.000 | 0.444 | 2 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 7 | 0.360 | 0.286 |
| 0.6–0.7 | 2 | 0.640 | 0.000 |
| 0.8–0.9 | 1 | 0.810 | 1.000 |

## Provider: anthropic

- Clips: 10  ·  Accuracy: 30%  ·  Macro P/R/F1: 0.429 / 0.400 / 0.259
- Cohen's kappa: 0.067  ·  MCC: 0.094  ·  ECE: 0.199  ·  Brier: 0.232  ·  Mean confidence: 0.461
- Latency ms — mean 88.358 · p50 86.290 · p95 97.856 · max 104.905

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 1 | 2 | 2 |
| bad_call | 0 | 0 | 3 |
| inconclusive | 0 | 0 | 2 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 1.000 | 0.200 | 0.333 | 5 |
| bad_call | 0.000 | 0.000 | 0.000 | 3 |
| inconclusive | 0.286 | 1.000 | 0.444 | 2 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 7 | 0.360 | 0.286 |
| 0.6–0.7 | 2 | 0.640 | 0.000 |
| 0.8–0.9 | 1 | 0.810 | 1.000 |

## Provider: gemini

- Clips: 10  ·  Accuracy: 30%  ·  Macro P/R/F1: 0.429 / 0.400 / 0.259
- Cohen's kappa: 0.067  ·  MCC: 0.094  ·  ECE: 0.199  ·  Brier: 0.232  ·  Mean confidence: 0.461
- Latency ms — mean 86.483 · p50 86.409 · p95 87.325 · max 87.492

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 1 | 2 | 2 |
| bad_call | 0 | 0 | 3 |
| inconclusive | 0 | 0 | 2 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 1.000 | 0.200 | 0.333 | 5 |
| bad_call | 0.000 | 0.000 | 0.000 | 3 |
| inconclusive | 0.286 | 1.000 | 0.444 | 2 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 7 | 0.360 | 0.286 |
| 0.6–0.7 | 2 | 0.640 | 0.000 |
| 0.8–0.9 | 1 | 0.810 | 1.000 |
