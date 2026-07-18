# RefCheck AI — Evaluation Benchmark

- Dataset: `data/eval/benchmark_lacrosse.json`  ·  Detector: `claude_vision`  ·  Clips: 6
- Generated: `2026-07-18T02:59:49.735775+00:00`

## Provider comparison

| Provider | Accuracy | Macro F1 | Kappa | ECE | MCC | Brier | Mean latency (ms) | p95 (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mock | 17% | 0.095 | 0.000 | 0.193 | 0.000 | 0.176 | 88.766 | 92.802 |
| anthropic ★ | 17% | 0.095 | 0.000 | 0.193 | 0.000 | 0.176 | 85.366 | 88.052 |
| gemini | 17% | 0.095 | 0.000 | 0.193 | 0.000 | 0.176 | 86.535 | 86.923 |

**Recommended provider: `anthropic`** ★ — highest accuracy, then Matthews correlation, then best-calibrated (lowest Brier), then fastest.

## Provider: mock

- Clips: 6  ·  Accuracy: 17%  ·  Macro P/R/F1: 0.056 / 0.333 / 0.095
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.193  ·  Brier: 0.176  ·  Mean confidence: 0.360
- Latency ms — mean 88.766 · p50 87.815 · p95 92.802 · max 93.963

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 0 | 0 | 4 |
| bad_call | 0 | 0 | 1 |
| inconclusive | 0 | 0 | 1 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.000 | 0.000 | 0.000 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 1 |
| inconclusive | 0.167 | 1.000 | 0.286 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 6 | 0.360 | 0.167 |

## Provider: anthropic

- Clips: 6  ·  Accuracy: 17%  ·  Macro P/R/F1: 0.056 / 0.333 / 0.095
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.193  ·  Brier: 0.176  ·  Mean confidence: 0.360
- Latency ms — mean 85.366 · p50 86.105 · p95 88.052 · max 88.345

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 0 | 0 | 4 |
| bad_call | 0 | 0 | 1 |
| inconclusive | 0 | 0 | 1 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.000 | 0.000 | 0.000 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 1 |
| inconclusive | 0.167 | 1.000 | 0.286 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 6 | 0.360 | 0.167 |

## Provider: gemini

- Clips: 6  ·  Accuracy: 17%  ·  Macro P/R/F1: 0.056 / 0.333 / 0.095
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.193  ·  Brier: 0.176  ·  Mean confidence: 0.360
- Latency ms — mean 86.535 · p50 86.633 · p95 86.923 · max 86.933

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 0 | 0 | 4 |
| bad_call | 0 | 0 | 1 |
| inconclusive | 0 | 0 | 1 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.000 | 0.000 | 0.000 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 1 |
| inconclusive | 0.167 | 1.000 | 0.286 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 6 | 0.360 | 0.167 |
