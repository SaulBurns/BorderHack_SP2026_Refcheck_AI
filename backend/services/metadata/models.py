"""Typed models for sports metadata enrichment (Phase 10A, basketball/NBA only).

Additive layer: these describe optional game-context enrichment attached to the
analysis response. They never replace or alter the officiating verdict fields.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ResolutionStatus = Literal["resolved", "candidate_match", "unresolved", "skipped"]


class GameCandidate(BaseModel):
    """A single candidate game the clip might correspond to."""

    provider: Literal["nba"] = "nba"
    game_id: str
    game_date: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    home_team_code: str | None = None
    away_team_code: str | None = None
    status_text: str | None = None
    confidence: float | None = None
    match_reasons: list[str] = Field(default_factory=list)
    raw: dict | None = None


class ResolvedGameContext(BaseModel):
    """The result of attempting to resolve a clip to an NBA game."""

    provider: Literal["nba"] = "nba"
    game_id: str | None = None
    game_date: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    home_team_code: str | None = None
    away_team_code: str | None = None
    season: str | None = None
    quarter: str | None = None
    clock: str | None = None
    score_summary: str | None = None
    resolution_status: ResolutionStatus
    confidence: float | None = None
    match_reasons: list[str] = Field(default_factory=list)
    candidates: list[GameCandidate] = Field(default_factory=list)


class ClipMetadataRequest(BaseModel):
    """Everything we may know about an uploaded clip, fed to a metadata provider."""

    sport: str
    league: str | None = None
    original_call: str | None = None
    video_filename: str | None = None
    video_created_at: str | None = None
    clip_date_hint: str | None = None
    home_team_hint: str | None = None
    away_team_hint: str | None = None
    broadcast_hint: str | None = None
    manual_game_id: str | None = None
