"""Static NBA team table + deterministic text matching (no network, no AI).

Kept static so hint extraction works without nba_api installed and is fully
testable. Abbreviation matches require the token to be UPPERCASE in the source
text (e.g. "LAL" in a filename) to avoid false positives from common English
words like "was" (WAS) or "min".
"""

from __future__ import annotations

import re

# abbr, city, nickname
_NBA_TEAMS: list[tuple[str, str, str]] = [
    ("ATL", "Atlanta", "Hawks"),
    ("BOS", "Boston", "Celtics"),
    ("BKN", "Brooklyn", "Nets"),
    ("CHA", "Charlotte", "Hornets"),
    ("CHI", "Chicago", "Bulls"),
    ("CLE", "Cleveland", "Cavaliers"),
    ("DAL", "Dallas", "Mavericks"),
    ("DEN", "Denver", "Nuggets"),
    ("DET", "Detroit", "Pistons"),
    ("GSW", "Golden State", "Warriors"),
    ("HOU", "Houston", "Rockets"),
    ("IND", "Indiana", "Pacers"),
    ("LAC", "Los Angeles", "Clippers"),
    ("LAL", "Los Angeles", "Lakers"),
    ("MEM", "Memphis", "Grizzlies"),
    ("MIA", "Miami", "Heat"),
    ("MIL", "Milwaukee", "Bucks"),
    ("MIN", "Minnesota", "Timberwolves"),
    ("NOP", "New Orleans", "Pelicans"),
    ("NYK", "New York", "Knicks"),
    ("OKC", "Oklahoma City", "Thunder"),
    ("ORL", "Orlando", "Magic"),
    ("PHI", "Philadelphia", "76ers"),
    ("PHX", "Phoenix", "Suns"),
    ("POR", "Portland", "Trail Blazers"),
    ("SAC", "Sacramento", "Kings"),
    ("SAS", "San Antonio", "Spurs"),
    ("TOR", "Toronto", "Raptors"),
    ("UTA", "Utah", "Jazz"),
    ("WAS", "Washington", "Wizards"),
]

ABBRS: set[str] = {abbr for abbr, _, _ in _NBA_TEAMS}

TEAM_NAME_BY_ABBR: dict[str, str] = {abbr: f"{city} {nick}" for abbr, city, nick in _NBA_TEAMS}
TEAM_NICKNAME_BY_ABBR: dict[str, str] = {abbr: nick for abbr, _, nick in _NBA_TEAMS}

# Single lowercase token -> abbr (unambiguous nicknames + common short forms).
_SINGLE_TOKEN_MAP: dict[str, str] = {}
for _abbr, _city, _nick in _NBA_TEAMS:
    if " " not in _nick:  # single-word nickname
        _SINGLE_TOKEN_MAP[_nick.lower()] = _abbr
_SINGLE_TOKEN_MAP.update(
    {
        "cavs": "CLE",
        "sixers": "PHI",
        "blazers": "POR",
        "wolves": "MIN",
        "mavs": "DAL",
        "dubs": "GSW",
        "pels": "NOP",
        "grizz": "MEM",
        "nuggs": "DEN",
        "wiz": "WAS",
    }
)

# Multi-word phrases scanned as substrings (lowercased).
_MULTIWORD_NAMES: list[tuple[str, str]] = [
    ("trail blazers", "POR"),
    ("portland trail blazers", "POR"),
    ("los angeles lakers", "LAL"),
    ("los angeles clippers", "LAC"),
    ("golden state warriors", "GSW"),
    ("new york knicks", "NYK"),
    ("new orleans pelicans", "NOP"),
    ("oklahoma city thunder", "OKC"),
    ("san antonio spurs", "SAS"),
]


def find_team_abbrs(text: str | None) -> list[str]:
    """Return NBA team abbreviations detected in text, in order, de-duplicated.

    - Uppercase 3-letter abbreviations (e.g. "LAL") match directly.
    - Single-word nicknames / aliases (e.g. "lakers", "cavs") match case-insensitively.
    - Multi-word names (e.g. "trail blazers") match as substrings.
    """
    if not text:
        return []
    found: list[str] = []

    def _add(abbr: str) -> None:
        if abbr not in found:
            found.append(abbr)

    for token in re.split(r"[^A-Za-z0-9]+", text):
        if not token:
            continue
        if token.isupper() and len(token) == 3 and token in ABBRS:
            _add(token)
        mapped = _SINGLE_TOKEN_MAP.get(token.lower())
        if mapped:
            _add(mapped)

    lowered = text.lower()
    for phrase, abbr in _MULTIWORD_NAMES:
        if phrase in lowered:
            _add(abbr)

    return found


def normalize_team_hint(value: str | None) -> str | None:
    """Resolve a free-form team hint (abbr, nickname, or name) to an abbreviation."""
    if not value:
        return None
    value = value.strip()
    if value.upper() in ABBRS:
        return value.upper()
    abbrs = find_team_abbrs(value)
    return abbrs[0] if abbrs else None
