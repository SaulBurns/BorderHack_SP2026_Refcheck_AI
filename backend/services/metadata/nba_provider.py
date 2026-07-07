"""NBA metadata provider (Phase 10A).

Resolves a basketball clip to an NBA game using nba_api, conservatively:
  1. leaguegamefinder.LeagueGameFinder  - primary candidate search (by season/date)
  2. boxscoresummaryv2.BoxScoreSummaryV2 - enrich a resolved game (status/score/period)
  3. scoreboardv2.ScoreboardV2           - optional; not required by the default flow

nba_api is imported lazily inside the fetcher, so the whole subsystem works (and
is fully tested) without it installed. All failures degrade to "unresolved".
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from services.metadata.cache import TTLCache
from services.metadata.hints import ClipHints, extract_hints
from services.metadata.models import ClipMetadataRequest, ResolvedGameContext
from services.metadata.ranking import decide_resolution, score_candidates
from services.metadata.teams import TEAM_NAME_BY_ABBR

_DEFAULT_CACHE = TTLCache(ttl_seconds=900.0)


# ---------------------------------------------------------------------------
# nba_api access (lazy, isolated, mockable)
# ---------------------------------------------------------------------------

def _rows_from_result_set(result_set: dict) -> list[dict]:
    headers = result_set.get("headers", [])
    return [dict(zip(headers, row)) for row in result_set.get("rowSet", [])]


def _find_result_set(payload: dict, name: str) -> list[dict]:
    for result_set in payload.get("resultSets", []) or []:
        if result_set.get("name") == name:
            return _rows_from_result_set(result_set)
    return []


class NbaApiFetcher:
    """Thin wrapper over nba_api endpoints. Lazy imports; raises if unavailable."""

    def find_games(self, season: str | None, date_from: str | None, date_to: str | None) -> list[dict]:
        from nba_api.stats.endpoints import leaguegamefinder

        finder = leaguegamefinder.LeagueGameFinder(
            league_id_nullable="00",
            season_nullable=season or "",
            date_from_nullable=date_from or "",
            date_to_nullable=date_to or "",
        )
        payload = finder.get_dict()
        result_sets = payload.get("resultSets", [])
        return _rows_from_result_set(result_sets[0]) if result_sets else []

    def box_score_summary(self, game_id: str) -> dict:
        from nba_api.stats.endpoints import boxscoresummaryv2

        return boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id).get_dict()


# ---------------------------------------------------------------------------
# Parsing helpers (pure)
# ---------------------------------------------------------------------------

def _iso_to_mmddyyyy(iso_date: str, offset_days: int = 0) -> str | None:
    try:
        day = date.fromisoformat(iso_date) + timedelta(days=offset_days)
    except ValueError:
        return None
    return day.strftime("%m/%d/%Y")


def _games_from_rows(rows: list[dict]) -> list[dict]:
    """Collapse LeagueGameFinder team-rows into per-game candidate dicts."""
    games: dict[str, dict] = {}
    for row in rows:
        game_id = str(row.get("GAME_ID") or "")
        matchup = str(row.get("MATCHUP") or "")
        team = str(row.get("TEAM_ABBREVIATION") or "")
        if not game_id or not matchup or not team:
            continue
        parts = matchup.replace(".", "").split()
        opponent = parts[-1] if parts else ""
        is_home = "vs" in matchup.lower()
        home_code, away_code = (team, opponent) if is_home else (opponent, team)

        game = games.setdefault(
            game_id,
            {
                "game_id": game_id,
                "game_date": str(row.get("GAME_DATE") or "")[:10] or None,
                "home_team_code": home_code,
                "away_team_code": away_code,
                "home_pts": None,
                "away_pts": None,
            },
        )
        pts = row.get("PTS")
        if pts is not None:
            if team == game["home_team_code"]:
                game["home_pts"] = pts
            elif team == game["away_team_code"]:
                game["away_pts"] = pts
    return list(games.values())


def _score_summary_from_game(game: dict) -> str | None:
    home_pts, away_pts = game.get("home_pts"), game.get("away_pts")
    if home_pts is None or away_pts is None:
        return None
    return f"{game.get('away_team_code')} {away_pts} @ {game.get('home_team_code')} {home_pts}"


def _quarter_label(live_period: Any) -> str | None:
    try:
        period = int(live_period)
    except (TypeError, ValueError):
        return None
    if period <= 0:
        return None
    return f"Q{period}" if period <= 4 else f"OT{period - 4}"


def _parse_boxscore(payload: dict) -> dict:
    summary_rows = _find_result_set(payload, "GameSummary")
    line_rows = _find_result_set(payload, "LineScore")
    if not summary_rows:
        return {}
    summary = summary_rows[0]

    by_team_id: dict[Any, dict] = {row.get("TEAM_ID"): row for row in line_rows}
    home_id = summary.get("HOME_TEAM_ID")
    visitor_id = summary.get("VISITOR_TEAM_ID")
    home = by_team_id.get(home_id, {})
    away = by_team_id.get(visitor_id, {})

    score_summary = None
    if home.get("PTS") is not None and away.get("PTS") is not None:
        score_summary = (
            f"{away.get('TEAM_ABBREVIATION')} {away.get('PTS')} @ "
            f"{home.get('TEAM_ABBREVIATION')} {home.get('PTS')}"
        )

    return {
        "game_date": str(summary.get("GAME_DATE_EST") or "")[:10] or None,
        "home_team_code": home.get("TEAM_ABBREVIATION"),
        "away_team_code": away.get("TEAM_ABBREVIATION"),
        "season": (str(summary.get("SEASON")) if summary.get("SEASON") else None),
        "status_text": summary.get("GAME_STATUS_TEXT"),
        "quarter": _quarter_label(summary.get("LIVE_PERIOD")),
        "clock": summary.get("LIVE_PC_TIME") or None,
        "score_summary": score_summary,
    }


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class NBAMetadataProvider:
    provider_name = "nba"

    def __init__(self, fetcher: NbaApiFetcher | None = None, cache: TTLCache | None = None) -> None:
        self._fetcher = fetcher or NbaApiFetcher()
        self._cache = cache or _DEFAULT_CACHE

    def resolve_game_context(self, request: ClipMetadataRequest) -> ResolvedGameContext:
        try:
            return self._resolve(request)
        except Exception as exc:  # never break the pipeline
            return ResolvedGameContext(
                resolution_status="unresolved",
                match_reasons=[f"nba provider error: {type(exc).__name__}"],
            )

    # -- internal --------------------------------------------------------

    def _search_games(self, hints: ClipHints) -> list[dict]:
        date_from = _iso_to_mmddyyyy(hints.date_hint, -1) if hints.date_hint else None
        date_to = _iso_to_mmddyyyy(hints.date_hint, 1) if hints.date_hint else None
        key = f"games:{hints.season_hint}:{date_from}:{date_to}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        rows = self._fetcher.find_games(hints.season_hint, date_from, date_to)
        self._cache.set(key, rows)
        return rows

    def _boxscore(self, game_id: str) -> dict:
        key = f"box:{game_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        payload = self._fetcher.box_score_summary(game_id)
        self._cache.set(key, payload)
        return payload

    def _enrich_boxscore(self, game_id: str) -> dict:
        try:
            return _parse_boxscore(self._boxscore(game_id))
        except Exception:
            return {}

    def _resolve(self, request: ClipMetadataRequest) -> ResolvedGameContext:
        hints = extract_hints(request)

        # Case 1: explicit game id
        if request.manual_game_id:
            return self._resolve_by_game_id(str(request.manual_game_id))

        # Case 4: no usable hints
        if not hints.date_hint:
            if hints.team_hints:
                return ResolvedGameContext(
                    resolution_status="unresolved",
                    season=hints.season_hint,
                    match_reasons=[*hints.reasons, "team hint(s) found but no date to bound the NBA search"],
                )
            return ResolvedGameContext(
                resolution_status="skipped",
                match_reasons=["no date or team hints available"],
            )

        # Case 2/3: search by date window
        games = _games_from_rows(self._search_games(hints))
        if not games:
            return ResolvedGameContext(
                resolution_status="unresolved",
                season=hints.season_hint,
                match_reasons=[*hints.reasons, "no NBA games found near the clip date"],
            )

        scored = score_candidates(games, hints, request)
        status = decide_resolution(scored)
        candidates = [s.candidate for s in scored[:5]]
        top = scored[0].candidate
        games_by_id = {g["game_id"]: g for g in games}

        if status == "resolved":
            enriched = self._enrich_boxscore(top.game_id)
            return ResolvedGameContext(
                resolution_status="resolved",
                game_id=top.game_id,
                game_date=top.game_date,
                home_team=top.home_team,
                away_team=top.away_team,
                home_team_code=top.home_team_code,
                away_team_code=top.away_team_code,
                season=enriched.get("season") or hints.season_hint,
                quarter=enriched.get("quarter"),
                clock=enriched.get("clock"),
                score_summary=enriched.get("score_summary") or _score_summary_from_game(games_by_id[top.game_id]),
                confidence=top.confidence,
                match_reasons=[*hints.reasons, *top.match_reasons],
                candidates=candidates,
            )

        if status == "candidate_match":
            return ResolvedGameContext(
                resolution_status="candidate_match",
                game_id=top.game_id,
                game_date=top.game_date,
                home_team=top.home_team,
                away_team=top.away_team,
                home_team_code=top.home_team_code,
                away_team_code=top.away_team_code,
                season=hints.season_hint,
                score_summary=_score_summary_from_game(games_by_id[top.game_id]),
                confidence=top.confidence,
                match_reasons=[*hints.reasons, *top.match_reasons, "multiple plausible games; best guess shown"],
                candidates=candidates,
            )

        return ResolvedGameContext(
            resolution_status="unresolved",
            season=hints.season_hint,
            match_reasons=[*hints.reasons, "no confident game match"],
            candidates=candidates,
        )

    def _resolve_by_game_id(self, game_id: str) -> ResolvedGameContext:
        enriched = self._enrich_boxscore(game_id)
        if not enriched or not enriched.get("home_team_code"):
            return ResolvedGameContext(
                resolution_status="unresolved",
                game_id=game_id,
                match_reasons=["manual game_id provided but lookup returned no data"],
            )
        return ResolvedGameContext(
            resolution_status="resolved",
            game_id=game_id,
            game_date=enriched.get("game_date"),
            home_team=TEAM_NAME_BY_ABBR.get(enriched.get("home_team_code") or ""),
            away_team=TEAM_NAME_BY_ABBR.get(enriched.get("away_team_code") or ""),
            home_team_code=enriched.get("home_team_code"),
            away_team_code=enriched.get("away_team_code"),
            season=enriched.get("season"),
            quarter=enriched.get("quarter"),
            clock=enriched.get("clock"),
            score_summary=enriched.get("score_summary"),
            confidence=1.0,
            match_reasons=["manual game_id provided"],
        )
