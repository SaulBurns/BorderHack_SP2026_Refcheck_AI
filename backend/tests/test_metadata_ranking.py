import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.metadata.hints import ClipHints
from services.metadata.models import ClipMetadataRequest
from services.metadata.ranking import decide_resolution, score_candidates


def _req(**kwargs):
    return ClipMetadataRequest(sport="basketball", **kwargs)


def _game(game_id, game_date, home, away, home_pts=None, away_pts=None):
    return {
        "game_id": game_id,
        "game_date": game_date,
        "home_team_code": home,
        "away_team_code": away,
        "home_pts": home_pts,
        "away_pts": away_pts,
    }


def test_exact_team_and_date_ranks_above_weak():
    games = [
        _game("A", "2024-12-25", "LAL", "BOS"),  # exact date + both teams
        _game("B", "2024-12-24", "MIA", "NYK"),  # within a day, no team
    ]
    hints = ClipHints(date_hint="2024-12-25", season_hint="2024-25", team_hints=("LAL", "BOS"))
    scored = score_candidates(games, hints, _req(league="NBA"))
    assert scored[0].candidate.game_id == "A"
    assert scored[0].candidate.confidence == 1.0
    assert scored[0].score > scored[1].score

def test_exact_unique_match_resolves():
    games = [_game("A", "2024-12-25", "LAL", "BOS")]
    hints = ClipHints(date_hint="2024-12-25", team_hints=("LAL", "BOS"))
    scored = score_candidates(games, hints, _req())
    assert decide_resolution(scored) == "resolved"

def test_ambiguous_date_only_is_candidate_match_not_certainty():
    # Two games on the same date, no team hint -> cannot be certain.
    games = [
        _game("A", "2024-12-25", "LAL", "BOS"),
        _game("B", "2024-12-25", "MIA", "NYK"),
    ]
    hints = ClipHints(date_hint="2024-12-25", team_hints=())
    scored = score_candidates(games, hints, _req())
    assert decide_resolution(scored) == "candidate_match"
    assert scored[0].candidate.confidence is not None and scored[0].candidate.confidence < 1.0

def test_no_signal_is_unresolved():
    games = [_game("A", "2024-01-01", "LAL", "BOS")]
    hints = ClipHints(date_hint="2024-12-25", team_hints=("MIA",))  # wrong date, wrong team
    scored = score_candidates(games, hints, _req())
    assert decide_resolution(scored) == "unresolved"

def test_empty_candidates_unresolved():
    assert decide_resolution([]) == "unresolved"

def test_match_reasons_are_transparent():
    games = [_game("A", "2024-12-25", "LAL", "BOS")]
    hints = ClipHints(date_hint="2024-12-25", team_hints=("LAL",))
    scored = score_candidates(games, hints, _req(league="NBA"))
    reasons = scored[0].candidate.match_reasons
    assert "exact game date match" in reasons
    assert "team match: LAL" in reasons
    assert "league hint mentions NBA" in reasons
