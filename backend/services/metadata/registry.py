"""Metadata provider registry + orchestration (Phase 10A).

Basketball-only for now: only "basketball" maps to a provider. Every other sport
returns None, so non-basketball flows are untouched.
"""

from __future__ import annotations

from services.metadata.base import MetadataProvider
from services.metadata.models import ClipMetadataRequest, ResolvedGameContext
from services.metadata.nba_provider import NBAMetadataProvider


def get_metadata_provider(sport: str) -> MetadataProvider | None:
    """Return the metadata provider for a sport, or None if unsupported."""
    if (sport or "").lower().strip() == "basketball":
        return NBAMetadataProvider()
    return None


def resolve_clip_game_context(
    *,
    sport: str,
    league: str | None = None,
    original_call: str | None = None,
    video_metadata: dict | None = None,
    manual_game_id: str | None = None,
) -> ResolvedGameContext | None:
    """Resolve game context for a clip. Returns None for non-basketball sports.

    Never raises: any provider failure degrades to an "unresolved" context so the
    core officiating verdict is never affected.
    """
    provider = get_metadata_provider(sport)
    if provider is None:
        return None

    metadata = video_metadata or {}
    request = ClipMetadataRequest(
        sport=sport,
        league=league,
        original_call=original_call,
        video_filename=metadata.get("filename"),
        manual_game_id=manual_game_id,
    )
    try:
        return provider.resolve_game_context(request)
    except Exception as exc:
        return ResolvedGameContext(
            resolution_status="unresolved",
            match_reasons=[f"metadata enrichment error: {type(exc).__name__}"],
        )
