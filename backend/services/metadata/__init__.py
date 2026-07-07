"""Sports metadata enrichment (Phase 10A — basketball/NBA only).

Additive layer that resolves an uploaded clip to an NBA game and exposes an
optional `game_context` block on the analysis response. It never alters the
officiating verdict, and does nothing for non-basketball sports.
"""

from services.metadata.models import (
    ClipMetadataRequest,
    GameCandidate,
    ResolvedGameContext,
)
from services.metadata.nba_provider import NBAMetadataProvider
from services.metadata.registry import get_metadata_provider, resolve_clip_game_context

__all__ = [
    "ClipMetadataRequest",
    "GameCandidate",
    "ResolvedGameContext",
    "NBAMetadataProvider",
    "get_metadata_provider",
    "resolve_clip_game_context",
]
