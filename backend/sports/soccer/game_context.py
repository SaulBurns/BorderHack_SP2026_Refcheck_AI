"""Soccer game-context provider (Sprint 10).

The game-context (metadata enrichment) layer resolves an uploaded clip to a real
match so the response can carry an optional ``game_context`` block. That layer is
backed by a sport-specific data source; basketball ships the NBA provider. Soccer
has no match database wired in Sprint 10, so this returns ``None`` — the metadata
registry's documented "no provider" path, which leaves the officiating verdict
and the response contract completely unchanged (no ``game_context`` block for
soccer, exactly as before).

This module is the single, obvious seam for adding real soccer enrichment later:
implement a ``MetadataProvider`` (``services/metadata/base.py``) backed by a
fixtures/results source (e.g. an open football-data API) and return it here;
``SoccerSport.metadata_provider()`` and the metadata registry pick it up with no
pipeline changes.
"""

from __future__ import annotations

from typing import Any


def soccer_metadata_provider() -> Any | None:
    """Return the soccer game-context provider, or None when none is configured.

    Returns None in Sprint 10: soccer has no match-resolution data source yet, so
    clips get Claude-only analysis with no game-context enrichment.
    """
    return None
