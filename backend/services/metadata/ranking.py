"""Deterministic candidate ranking (no AI).

Scores candidate NBA games against extracted hints and decides how confident the
resolution is. Transparent and testable — every point comes with a reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from services.metadata.hints import ClipHints
from services.metadata.models import ClipMetadataRequest, GameCandidate
from services.metadata.teams import TEAM_NAME_BY_ABBR

# Confidence denominator: a same-date, both-teams, NBA-league match scores well
# above this and caps at 1.0; a single team + date lands around 0.6.
_CONFIDENCE_DENOM = 15.0


@dataclass
class ScoredCandidate:
    candidate: GameCandidate
    score: int
    date_exact: bool
    team_matches: int


def _within_one_day(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    try:
        da = date.fromisoformat(a)
        db = date.fromisoformat(b)
    except ValueError:
        return False
    return abs((da - db).days) <= 1


def _score(game: dict, hints: ClipHints, request: ClipMetadataRequest) -> ScoredCandidate:
    score = 0
    reasons: list[str] = []
    game_date = game.get("game_date")

    date_exact = bool(hints.date_hint and game_date == hints.date_hint)
    if date_exact:
        score += 5
        reasons.append("exact game date match")
    elif hints.date_hint and _within_one_day(game_date, hints.date_hint):
        score += 2
        reasons.append("date within ±1 day of hint")

    codes = {game.get("home_team_code"), game.get("away_team_code")}
    team_matches = 0
    for abbr in hints.team_hints:
        if abbr in codes:
            score += 4
            team_matches += 1
            reasons.append(f"team match: {abbr}")
    if team_matches >= 2:
        score += 3
        reasons.append("both team hints matched")

    if request.league and "nba" in request.league.lower():
        score += 1
        reasons.append("league hint mentions NBA")

    confidence = round(min(1.0, score / _CONFIDENCE_DENOM), 2)
    home_code = game.get("home_team_code")
    away_code = game.get("away_team_code")
    candidate = GameCandidate(
        game_id=str(game.get("game_id", "")),
        game_date=game_date,
        home_team_code=home_code,
        away_team_code=away_code,
        home_team=TEAM_NAME_BY_ABBR.get(home_code or ""),
        away_team=TEAM_NAME_BY_ABBR.get(away_code or ""),
        status_text=game.get("status_text"),
        confidence=confidence,
        match_reasons=reasons,
    )
    return ScoredCandidate(candidate=candidate, score=score, date_exact=date_exact, team_matches=team_matches)


def score_candidates(
    games: list[dict],
    hints: ClipHints,
    request: ClipMetadataRequest,
) -> list[ScoredCandidate]:
    """Score and sort candidate games (best first)."""
    scored = [_score(game, hints, request) for game in games]
    scored.sort(key=lambda s: (s.score, s.candidate.game_id), reverse=True)
    return scored


def decide_resolution(scored: list[ScoredCandidate]) -> str:
    """Decide resolution status from ranked candidates. Never overclaims."""
    if not scored:
        return "unresolved"
    top = scored[0]
    runner_up_score = scored[1].score if len(scored) > 1 else 0
    is_unique_top = len(scored) == 1 or (top.score - runner_up_score) >= 4

    if top.date_exact and top.team_matches >= 1 and is_unique_top:
        return "resolved"
    if top.score >= 4:
        return "candidate_match"
    return "unresolved"
