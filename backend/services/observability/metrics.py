"""In-process metrics registry with Prometheus text-exposition output (Sprint 15).

Dependency-free (no prometheus_client): a small, thread-safe registry of counters
and latency summaries that renders the standard Prometheus text format, so the
`/api/metrics` endpoint scrapes cleanly with any Prometheus/Grafana/Datadog agent.

Thread-safe because `analyze_clip` runs on a worker thread (Sprint 6) and the two
adjudicators run on a ThreadPoolExecutor, so counters can be touched concurrently.
"""

from __future__ import annotations

import threading
from typing import Iterable

# Label sets are stored as a sorted tuple of (key, value) pairs so equal label
# dicts map to the same series regardless of insertion order.
_Labels = tuple[tuple[str, str], ...]


def _freeze(labels: dict[str, str] | None) -> _Labels:
    if not labels:
        return ()
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


def _render_labels(labels: _Labels) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{_escape(v)}"' for k, v in labels)
    return "{" + inner + "}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class MetricsRegistry:
    """Counters + latency summaries, rendered as Prometheus text.

    - `inc(name, labels, amount)` — monotonic counter.
    - `observe(name, labels, value)` — summary (exposes `_count` and `_sum`),
      used for request/pipeline latencies.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[_Labels, float]] = {}
        self._summaries: dict[str, dict[_Labels, list[float]]] = {}
        self._help: dict[str, str] = {}

    def describe(self, name: str, help_text: str) -> None:
        with self._lock:
            self._help.setdefault(name, help_text)

    def inc(self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        key = _freeze(labels)
        with self._lock:
            series = self._counters.setdefault(name, {})
            series[key] = series.get(key, 0.0) + amount

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = _freeze(labels)
        with self._lock:
            series = self._summaries.setdefault(name, {})
            bucket = series.setdefault(key, [0.0, 0.0])  # [count, sum]
            bucket[0] += 1
            bucket[1] += value

    def counter_value(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Read one counter series (used by tests and health)."""
        with self._lock:
            return self._counters.get(name, {}).get(_freeze(labels), 0.0)

    def reset(self) -> None:
        """Clear all series (test isolation)."""
        with self._lock:
            self._counters.clear()
            self._summaries.clear()

    def render(self) -> str:
        """Prometheus text-exposition format (v0.0.4)."""
        with self._lock:
            lines: list[str] = []
            for name in sorted(self._counters):
                lines.extend(self._render_help(name, "counter"))
                for labels, value in sorted(self._counters[name].items()):
                    lines.append(f"{name}{_render_labels(labels)} {_num(value)}")
            for name in sorted(self._summaries):
                lines.extend(self._render_help(name, "summary"))
                for labels, (count, total) in sorted(self._summaries[name].items()):
                    lines.append(f"{name}_count{_render_labels(labels)} {_num(count)}")
                    lines.append(f"{name}_sum{_render_labels(labels)} {_num(total)}")
            return "\n".join(lines) + ("\n" if lines else "")

    def _render_help(self, name: str, metric_type: str) -> Iterable[str]:
        help_text = self._help.get(name)
        out = []
        if help_text:
            out.append(f"# HELP {name} {help_text}")
        out.append(f"# TYPE {name} {metric_type}")
        return out


def _num(value: float) -> str:
    """Render a float without a trailing .0 for integers (cleaner exposition)."""
    return str(int(value)) if float(value).is_integer() else repr(value)


# The process-wide default registry the app and pipeline write to.
metrics = MetricsRegistry()
metrics.describe("refcheck_http_requests_total", "Total HTTP requests by method, path, status.")
metrics.describe("refcheck_http_request_duration_seconds", "HTTP request duration in seconds.")
metrics.describe("refcheck_analyses_total", "Completed clip analyses by sport and verdict.")
metrics.describe("refcheck_rate_limited_total", "Requests rejected by the rate limiter.")
metrics.describe("refcheck_auth_failures_total", "Requests rejected for a missing/invalid API key.")
