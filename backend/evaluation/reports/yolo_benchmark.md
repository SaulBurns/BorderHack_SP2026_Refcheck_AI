# YOLO detector benchmark (Sprint 18A)

- Mode: `live`  ·  Detector version: `0.3.0`  ·  Default weights: `yolo26n.pt`

| Config | Model | Precision | Recall | F1 | ID switches | Track purity | Matched | Latency (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| before | `yolov8n.pt` | — | — | — | — | — | — | 422.65 |
| after | `yolo26n.pt` | — | — | — | — | — | — | 403.68 |

_Live run without `--truth`: **latency only** — warm-model steady-state (one-time torch + weights load excluded); add `--truth <RawDetections JSON>` over labeled footage for detection accuracy + tracking quality._
