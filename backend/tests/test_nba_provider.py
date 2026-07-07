import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.metadata.cache import TTLCache
from services.metadata.models import ClipMetadataRequest
from services.metadata.nba_provider import NBAMetadataProvider

# --- Sample nba_api payloads (LeagueGameFinder rows + BoxScoreSummaryV2) ------

_GAME_ROWS = [
    {"GAME_ID": "0022400500", "GAME_DATE": "2024-12-25", "MATCHUP": "LAL vs. BOS", "TEAM_ABBREVIATION": "LAL", "PTS": 115},
    {"GAME_ID": "0022400500", "GAME_DATE": "2024-12-25", "MATCHUP": "BOS @ LAL", "TEAM_ABBREVIATION": "BOS", "PTS": 110},
]

_BOXSCORE = {
    "resultSets": [
        {
            "name": "GameSummary",
            "headers": ["GAME_DATE_EST", "GAME_STATUS_TEXT", "HOME_TEAM_ID", "VISITOR_TEAM_ID", "SEASON", "LIVE_PERIOD", "LIVE_PC_TIME"],
            "rowSet": [["2024-12-25T00:00:00", "Final", 1610612747, 1610612738, "2024", 4, "0:00"]],
        },
        {
            "name": "LineScore",
            "headers": ["TEAM_ID", "TEAM_ABBREVIATION", "PTS"],
            "rowSet": [[1610612747, "LAL", 115], [1610612738, "BOS", 110]],
        },
    ]
}


class FakeFetcher:
    def __init__(self, game_rows=None, boxscore=None, raise_on=None):
        self.game_rows = game_rows if game_rows is not None else _GAME_ROWS
        self.boxscore = boxscore if boxscore is not None else _BOXSCORE
        self.raise_on = raise_on
        self.find_calls = 0

    def find_games(self, season, date_from, date_to):
        self.find_calls += 1
        if self.raise_on == "find":
            raise RuntimeError("nba_api boom")
        return self.game_rows

    def box_score_summary(self, game_id):
        if self.raise_on == "box":
            raise RuntimeError("nba_api boom")
        return self.boxscore


def _provider(fetcher):
    return NBAMetadataProvider(fetcher=fetcher, cache=TTLCache())


def _req(**kwargs):
    return ClipMetadataRequest(sport="basketball", **kwargs)


# ---------------------------------------------------------------------------

def test_manual_game_id_resolves():
    ctx = _provider(FakeFetcher()).resolve_game_context(_req(manual_game_id="0022400500"))
    assert ctx.resolution_status == "resolved"
    assert ctx.game_id == "0022400500"
    assert ctx.home_team_code == "LAL"
    assert ctx.away_team_code == "BOS"
    assert ctx.confidence == 1.0
    assert ctx.score_summary == "BOS 110 @ LAL 115"
    assert ctx.quarter == "Q4"
    assert "manual game_id provided" in ctx.match_reasons

def test_date_and_team_resolves():
    ctx = _provider(FakeFetcher()).resolve_game_context(
        _req(video_filename="LAL_vs_BOS_2024-12-25.mp4", league="NBA")
    )
    assert ctx.resolution_status == "resolved"
    assert ctx.game_id == "0022400500"
    assert ctx.home_team == "Los Angeles Lakers"
    assert ctx.away_team == "Boston Celtics"
    assert ctx.season == "2024"  # from box score enrichment
    assert ctx.score_summary == "BOS 110 @ LAL 115"
    assert len(ctx.candidates) == 1

def test_date_only_multiple_games_is_candidate_match():
    rows = _GAME_ROWS + [
        {"GAME_ID": "0022400501", "GAME_DATE": "2024-12-25", "MATCHUP": "MIA vs. NYK", "TEAM_ABBREVIATION": "MIA", "PTS": 100},
        {"GAME_ID": "0022400501", "GAME_DATE": "2024-12-25", "MATCHUP": "NYK @ MIA", "TEAM_ABBREVIATION": "NYK", "PTS": 98},
    ]
    ctx = _provider(FakeFetcher(game_rows=rows)).resolve_game_context(
        _req(video_filename="christmas_game_2024-12-25.mp4")
    )
    assert ctx.resolution_status == "candidate_match"
    assert len(ctx.candidates) == 2

def test_no_games_found_is_unresolved():
    ctx = _provider(FakeFetcher(game_rows=[])).resolve_game_context(
        _req(video_filename="clip_2024-12-25.mp4")
    )
    assert ctx.resolution_status == "unresolved"

def test_provider_exception_is_swallowed_to_unresolved():
    ctx = _provider(FakeFetcher(raise_on="find")).resolve_game_context(
        _req(video_filename="LAL_vs_BOS_2024-12-25.mp4")
    )
    assert ctx.resolution_status == "unresolved"
    assert any("error" in r.lower() for r in ctx.match_reasons)

def test_no_hints_is_skipped():
    ctx = _provider(FakeFetcher()).resolve_game_context(_req(video_filename="random_clip.mp4"))
    assert ctx.resolution_status == "skipped"

def test_teams_but_no_date_is_unresolved_without_search():
    fetcher = FakeFetcher()
    ctx = _provider(fetcher).resolve_game_context(_req(video_filename="LAL_at_BOS.mp4"))
    assert ctx.resolution_status == "unresolved"
    assert fetcher.find_calls == 0  # never searched (no date to bound the query)

def test_search_results_are_cached():
    fetcher = FakeFetcher()
    provider = _provider(fetcher)
    req = _req(video_filename="LAL_vs_BOS_2024-12-25.mp4")
    provider.resolve_game_context(req)
    provider.resolve_game_context(req)
    assert fetcher.find_calls == 1  # second call served from cache
