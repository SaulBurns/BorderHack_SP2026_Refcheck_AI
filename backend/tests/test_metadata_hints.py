import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.metadata.hints import extract_hints, parse_date, season_from_date
from services.metadata.models import ClipMetadataRequest
from services.metadata.teams import find_team_abbrs, normalize_team_hint


def _req(**kwargs):
    return ClipMetadataRequest(sport="basketball", **kwargs)


# ---------------------------------------------------------------------------
# Date parsing / season
# ---------------------------------------------------------------------------

def test_parse_date_iso():
    assert parse_date("LAL_vs_BOS_2024-12-25.mp4") == "2024-12-25"

def test_parse_date_mmddyyyy():
    assert parse_date("clip_12-25-2024.mov") == "2024-12-25"

def test_parse_date_compact():
    assert parse_date("game_20241225_highlight.mp4") == "2024-12-25"

def test_parse_date_none():
    assert parse_date("random_clip.mp4") is None

def test_parse_date_rejects_invalid():
    assert parse_date("2024-13-40.mp4") is None

def test_season_from_date_regular():
    assert season_from_date("2024-12-25") == "2024-25"
    assert season_from_date("2025-03-01") == "2024-25"
    assert season_from_date("2025-11-01") == "2025-26"


# ---------------------------------------------------------------------------
# Team detection
# ---------------------------------------------------------------------------

def test_find_teams_by_abbreviation():
    assert find_team_abbrs("LAL_vs_BOS_2024-12-25.mp4") == ["LAL", "BOS"]

def test_find_teams_by_name():
    assert find_team_abbrs("knicks-celtics-missed-charge.mov") == ["NYK", "BOS"]

def test_find_teams_multiword_name():
    assert find_team_abbrs("portland trail blazers comeback") == ["POR"]

def test_lowercase_abbr_not_matched_avoids_false_positive():
    # "was" (lowercase) must NOT match the WAS abbreviation.
    assert find_team_abbrs("that was a terrible call") == []

def test_uppercase_abbr_matched():
    assert find_team_abbrs("WAS at MIL recap") == ["WAS", "MIL"]

def test_nickname_matches_case_insensitive():
    assert find_team_abbrs("The Wizards got robbed") == ["WAS"]

def test_normalize_team_hint():
    assert normalize_team_hint("LAL") == "LAL"
    assert normalize_team_hint("Lakers") == "LAL"
    assert normalize_team_hint("Boston Celtics") == "BOS"
    assert normalize_team_hint("nonsense") is None


# ---------------------------------------------------------------------------
# extract_hints
# ---------------------------------------------------------------------------

def test_extract_hints_filename_with_teams_and_date():
    hints = extract_hints(_req(video_filename="LAL_vs_BOS_2024-12-25.mp4"))
    assert hints.date_hint == "2024-12-25"
    assert hints.team_hints == ("LAL", "BOS")
    assert hints.season_hint == "2024-25"

def test_extract_hints_filename_teams_only():
    hints = extract_hints(_req(video_filename="knicks-celtics-missed-charge.mov"))
    assert hints.date_hint is None
    assert hints.team_hints == ("NYK", "BOS")

def test_extract_hints_date_only():
    hints = extract_hints(_req(video_filename="clip_2025-01-15.mp4"))
    assert hints.date_hint == "2025-01-15"
    assert hints.team_hints == ()

def test_extract_hints_no_hints():
    hints = extract_hints(_req(video_filename="random_clip.mp4"))
    assert hints.date_hint is None
    assert hints.team_hints == ()

def test_extract_hints_from_original_call_and_explicit():
    hints = extract_hints(_req(original_call="Wizards blocking foul", home_team_hint="MIL"))
    assert "WAS" in hints.team_hints
    assert "MIL" in hints.team_hints
