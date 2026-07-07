"""Deterministic hint extraction from clip metadata (no AI, no network).

Turns a ClipMetadataRequest (filename, original call, league, explicit hints)
into structured signals a provider can use to search for a game.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.metadata.models import ClipMetadataRequest
from services.metadata.teams import find_team_abbrs, normalize_team_hint

# Date patterns, most specific first. All resolve to (year, month, day).
_DATE_PATTERNS: list[tuple[re.Pattern, tuple[int, int, int]]] = [
    (re.compile(r"(20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})"), (0, 1, 2)),  # YYYY-MM-DD
    (re.compile(r"(\d{1,2})[-_.](\d{1,2})[-_.](20\d{2})"), (2, 0, 1)),  # MM-DD-YYYY
    (re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"), (0, 1, 2)),   # YYYYMMDD
]


@dataclass(frozen=True)
class ClipHints:
    date_hint: str | None = None          # ISO YYYY-MM-DD
    season_hint: str | None = None        # e.g. "2024-25"
    team_hints: tuple[str, ...] = ()       # team abbreviations
    reasons: tuple[str, ...] = field(default_factory=tuple)


def _valid_date(year: int, month: int, day: int) -> str | None:
    if not (1990 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_date(text: str | None) -> str | None:
    """Extract the first plausible date (ISO) from text, or None."""
    if not text:
        return None
    for pattern, (yi, mi, di) in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            iso = _valid_date(int(groups[yi]), int(groups[mi]), int(groups[di]))
            if iso:
                return iso
    return None


def season_from_date(iso_date: str | None) -> str | None:
    """NBA season string for a date. Oct-Dec starts the season; Jan-Jun ends it."""
    if not iso_date:
        return None
    try:
        year, month, _ = (int(part) for part in iso_date.split("-"))
    except (ValueError, TypeError):
        return None
    start_year = year if month >= 10 else year - 1
    return f"{start_year}-{str(start_year + 1)[2:]}"


def extract_hints(request: ClipMetadataRequest) -> ClipHints:
    reasons: list[str] = []

    # --- Date ---
    date_hint = parse_date(request.clip_date_hint)
    if date_hint:
        reasons.append("date from clip_date_hint")
    if not date_hint:
        date_hint = parse_date(request.video_filename)
        if date_hint:
            reasons.append("date parsed from filename")
    if not date_hint:
        date_hint = parse_date(request.video_created_at)
        if date_hint:
            reasons.append("date from video_created_at")

    # --- Teams ---
    team_hints: list[str] = []

    def _add_team(abbr: str | None, reason: str) -> None:
        if abbr and abbr not in team_hints:
            team_hints.append(abbr)
            reasons.append(reason)

    _add_team(normalize_team_hint(request.home_team_hint), "home_team_hint provided")
    _add_team(normalize_team_hint(request.away_team_hint), "away_team_hint provided")
    for abbr in find_team_abbrs(request.video_filename):
        _add_team(abbr, f"team '{abbr}' found in filename")
    for abbr in find_team_abbrs(request.original_call):
        _add_team(abbr, f"team '{abbr}' found in original call")

    # --- Season ---
    season_hint = season_from_date(date_hint)
    if season_hint:
        reasons.append(f"season inferred: {season_hint}")

    return ClipHints(
        date_hint=date_hint,
        season_hint=season_hint,
        team_hints=tuple(team_hints),
        reasons=tuple(reasons),
    )
