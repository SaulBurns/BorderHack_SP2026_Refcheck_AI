"""Structured application logging (Sprint 15).

`configure_logging()` sets up the root logger once at app startup. Format and level
are env-driven and safe by default:

- `LOG_LEVEL` (default `INFO`).
- `LOG_FORMAT` = `json` (default, one JSON object per line — friendly to Render /
  CloudWatch / Datadog log pipelines) or `plain` (human-readable for local dev).

The JSON formatter emits any structured fields attached via `logger.info(..., extra=
{...})` (e.g. request_id, path, status, duration_ms), so request logs are queryable.
Dependency-free (stdlib `logging` + `json`).
"""

from __future__ import annotations

import json
import logging
import os

# Standard LogRecord attributes we never want to duplicate into the JSON payload;
# everything else attached via `extra=` is treated as a structured field.
_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonLogFormatter(logging.Formatter):
    """Render each log record as a single compact JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _resolve_level(explicit: str | None = None) -> int:
    name = (explicit or os.getenv("LOG_LEVEL") or "INFO").upper()
    return getattr(logging, name, logging.INFO)


def configure_logging(*, level: str | None = None, fmt: str | None = None) -> None:
    """Configure the root logger. Idempotent — safe to call more than once.

    Replaces the root handlers with a single stream handler using the JSON or plain
    formatter. Does not raise on an unknown level/format (falls back to sane
    defaults), so a misconfigured env var never crashes startup.
    """
    resolved_level = _resolve_level(level)
    resolved_fmt = (fmt or os.getenv("LOG_FORMAT") or "json").lower()

    handler = logging.StreamHandler()
    if resolved_fmt == "plain":
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    else:
        handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)
