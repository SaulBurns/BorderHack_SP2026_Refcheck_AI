"""Metadata provider protocol (Phase 10A)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from services.metadata.models import ClipMetadataRequest, ResolvedGameContext


@runtime_checkable
class MetadataProvider(Protocol):
    """A sport metadata provider that resolves a clip to a game context."""

    provider_name: str

    def resolve_game_context(self, request: ClipMetadataRequest) -> ResolvedGameContext:
        """Resolve (or fail to resolve) the clip to a game. Must never raise."""
        ...
