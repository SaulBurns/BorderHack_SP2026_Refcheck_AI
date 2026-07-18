# RefCheck AI — Evaluation Benchmark

- Dataset: `data/eval/benchmark_hockey.json`  ·  Detector: `claude_vision`  ·  Clips: 7
- Generated: `2026-07-18T02:59:47.751456+00:00`

## Provider comparison

| Provider | Accuracy | Macro F1 | Kappa | ECE | MCC | Brier | Mean latency (ms) | p95 (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mock | 14% | 0.083 | 0.000 | 0.217 | 0.000 | 0.170 | 87.341 | 94.382 |
| anthropic | 14% | 0.083 | 0.000 | 0.217 | 0.000 | 0.170 | 87.775 | 89.971 |
| gemini ★ | 14% | 0.083 | 0.000 | 0.217 | 0.000 | 0.170 | 87.415 | 90.263 |

**Recommended provider: `gemini`** ★ — highest accuracy, then Matthews correlation, then best-calibrated (lowest Brier), then fastest.

## Provider: mock

- Clips: 7  ·  Accuracy: 14%  ·  Macro P/R/F1: 0.048 / 0.333 / 0.083
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.217  ·  Brier: 0.170  ·  Mean confidence: 0.360
- Latency ms — mean 87.341 · p50 86.945 · p95 94.382 · max 97.185

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 0 | 0 | 4 |
| bad_call | 0 | 0 | 2 |
| inconclusive | 0 | 0 | 1 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.000 | 0.000 | 0.000 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 2 |
| inconclusive | 0.143 | 1.000 | 0.250 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 7 | 0.360 | 0.143 |

## Provider: anthropic

- Clips: 7  ·  Accuracy: 14%  ·  Macro P/R/F1: 0.048 / 0.333 / 0.083
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.217  ·  Brier: 0.170  ·  Mean confidence: 0.360
- Latency ms — mean 87.775 · p50 87.342 · p95 89.971 · max 90.410

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 0 | 0 | 4 |
| bad_call | 0 | 0 | 2 |
| inconclusive | 0 | 0 | 1 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.000 | 0.000 | 0.000 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 2 |
| inconclusive | 0.143 | 1.000 | 0.250 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 7 | 0.360 | 0.143 |

## Provider: gemini

- Clips: 7  ·  Accuracy: 14%  ·  Macro P/R/F1: 0.048 / 0.333 / 0.083
- Cohen's kappa: 0.000  ·  MCC: 0.000  ·  ECE: 0.217  ·  Brier: 0.170  ·  Mean confidence: 0.360
- Latency ms — mean 87.415 · p50 86.437 · p95 90.263 · max 90.315

### Confusion matrix (rows = ground truth, cols = predicted)

| GT \ Pred | fair_call | bad_call | inconclusive |
| --- | --- | --- | --- |
| fair_call | 0 | 0 | 4 |
| bad_call | 0 | 0 | 2 |
| inconclusive | 0 | 0 | 1 |

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| fair_call | 0.000 | 0.000 | 0.000 | 4 |
| bad_call | 0.000 | 0.000 | 0.000 | 2 |
| inconclusive | 0.143 | 1.000 | 0.250 | 1 |

### Confidence calibration (reliability)

| Confidence bin | Count | Avg confidence | Accuracy |
| --- | --- | --- | --- |
| 0.3–0.4 | 7 | 0.360 | 0.143 |
