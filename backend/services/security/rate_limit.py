"""Fixed-window in-process rate limiter (Sprint 15).

Pure and deterministic (the clock is injectable), so it is unit-testable without
sleeping. Keyed per client (IP, or API key when present). Off by default: it only
engages when `RATE_LIMIT_PER_MINUTE` is set to a positive integer.

In-process by design (single-instance / free-tier friendly). For a multi-replica
deployment, swap the backing store for Redis behind the same `allow()` seam — the
callers do not change.
"""

from __future__ import annotations

import os
import threading
import time

RATE_LIMIT_ENV = "RATE_LIMIT_PER_MINUTE"


def rate_limit_per_minute() -> int:
    """Configured requests-per-minute limit (0 or invalid => disabled)."""
    raw = os.getenv(RATE_LIMIT_ENV, "").strip()
    try:
        value = int(raw)
    except ValueError:
        return 0
    return value if value > 0 else 0


class RateLimiter:
    """Fixed-window counter per key.

    `allow(key, now)` returns `(allowed, retry_after_seconds)`. A window of
    `window_seconds` starts at the first request for a key; up to `limit` requests
    are allowed within it, after which requests are rejected until the window rolls
    over. `limit <= 0` disables limiting (always allowed).
    """

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # key -> (window_start, count)
        self._windows: dict[str, tuple[float, int]] = {}

    def allow(self, key: str, now: float | None = None) -> tuple[bool, float]:
        if self.limit <= 0:
            return True, 0.0
        current = time.monotonic() if now is None else now
        with self._lock:
            window_start, count = self._windows.get(key, (current, 0))
            if current - window_start >= self.window_seconds:
                # Window expired — start a fresh one.
                window_start, count = current, 0
            if count >= self.limit:
                retry_after = self.window_seconds - (current - window_start)
                return False, max(0.0, retry_after)
            self._windows[key] = (window_start, count + 1)
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()
