"""Lacrosse game-context provider (Sprint 12).

The game-context (metadata enrichment) layer resolves an uploaded clip to a real
game so the response can carry an optional ``game_context`` block. That layer is
backed by a sport-specific data source; basketball ships the NBA provider.
Lacrosse has no game database wired in Sprint 12, so this returns ``None`` — the
metadata registry's documented "no provider" path, which leaves the officiating
verdict and the response contract completely unchanged (no ``game_context`` block
for lacrosse, exactly as before).

This module is the single, obvious seam for adding real enrichment later:
implement a ``MetadataProvider`` (``services/metadata/base.py``) backed by a
schedule/results source and return it here; ``LacrosseSport.metadata_provider()``
and the metadata registry pick it up with no pipeline changes.
"""

from __future__ import annotations

from typing import Any


def lacrosse_metadata_provider() -> Any | None:
    """Return the lacrosse game-context provider, or None when none is configured.

    Returns None in Sprint 12: lacrosse has no game-resolution data source yet, so
    clips get Claude-only analysis with no game-context enrichment.
    """
    return None
