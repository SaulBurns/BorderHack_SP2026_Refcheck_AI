"""Generic name→class registry (Sprint 7).

The provider factory, detector registry, and extractor registry were three
near-identical implementations of the same register / available / create
boilerplate. This is the single shared implementation.

Their one *intentional* behavioral difference is expressed as the `fallback`
argument rather than duplicated as divergent code:

- Providers and detectors are explicit configuration (`AI_PROVIDER`, `DETECTOR`);
  an unknown value is a misconfiguration and should fail loudly -> no fallback,
  `create` raises `ValueError` listing the supported keys.
- Extractors are keyed by sport, which is normalized upstream and data-driven, so
  an unconfigured sport degrades gracefully -> `fallback=EmptyDetailExtractor`.

`create` calls the registered class with no arguments, so every registered
implementation must be constructible as `Cls()`.
"""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Maps normalized string keys to implementation classes."""

    def __init__(self, kind: str, *, fallback: type[T] | None = None) -> None:
        self._kind = kind
        self._fallback = fallback
        self._items: dict[str, type[T]] = {}

    def register(self, name: str, cls: type[T]) -> None:
        self._items[name.lower().strip()] = cls

    def available(self) -> list[str]:
        return sorted(self._items)

    def create(self, name: str | None = None) -> T:
        key = (name or "").strip().lower()
        cls = self._items.get(key)
        if cls is None:
            if self._fallback is not None:
                return self._fallback()
            raise ValueError(
                f"Unknown {self._kind} {key!r}. "
                f"Supported {self._kind}s: {', '.join(self.available())}."
            )
        return cls()
