"""Production observability: structured logging + in-process metrics (Sprint 15).

Pure, dependency-free building blocks (no prometheus_client / structlog needed):

- `logging_config.configure_logging()` — JSON or plain structured logs.
- `metrics.MetricsRegistry` — counters + latency summaries rendered in Prometheus
  text-exposition format, exposed at `/api/metrics`.

Everything is additive and safe by default, so it never changes the `/api/analyze`
response or breaks a run that sets no new env vars.
"""

from services.observability.logging_config import configure_logging
from services.observability.metrics import MetricsRegistry, metrics

__all__ = ["configure_logging", "MetricsRegistry", "metrics"]
