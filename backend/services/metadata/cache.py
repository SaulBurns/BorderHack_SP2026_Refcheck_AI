"""Tiny in-memory TTL cache to avoid hammering nba_api."""

from __future__ import annotations

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: float = 900.0, max_size: int = 256) -> None:
        self._ttl = ttl_seconds
        self._max = max_size
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        timestamp, value = item
        if time.time() - timestamp > self._ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if key not in self._store and len(self._store) >= self._max:
            oldest = min(self._store, key=lambda k: self._store[k][0])
            self._store.pop(oldest, None)
        self._store[key] = (time.time(), value)
