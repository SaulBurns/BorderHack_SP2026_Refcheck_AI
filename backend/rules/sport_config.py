from rules.basketball_rules import BASKETBALL_RULES
from rules.soccer_rules import SOCCER_RULES

SPORTS: dict[str, dict] = {
    "basketball": {
        "display_name": "Basketball",
        "rules": BASKETBALL_RULES,
    },
    "hockey": {
        "display_name": "Hockey",
        "rules": {},
    },
    "soccer": {
        "display_name": "Soccer",
        "rules": SOCCER_RULES,
    },
    "lacrosse": {
        "display_name": "Lacrosse",
        "rules": {},
    },
}

SUPPORTED_SPORTS: frozenset[str] = frozenset(SPORTS)


# NOTE: normalize_sport() and get_rules_for_sport() have different fallback behavior
# by design. normalize_sport() always returns a valid sport key (falling back to
# "basketball" for unknowns) and is called ONCE at the pipeline entry point.
# get_rules_for_sport() returns {} for unimplemented sports and is called with
# already-normalized values — it never sees unknown sport strings in production.


def normalize_sport(sport: str | None) -> str:
    """Lowercase and strip the value; return 'basketball' for unrecognized sports."""
    normalized = sport.lower().strip() if sport else ""
    return normalized if normalized in SPORTS else "basketball"


def get_rules_for_sport(sport: str) -> dict:
    """Return the rules dict for a sport.

    Returns an empty dict for unimplemented sports (hockey, soccer, lacrosse)
    and for unknown sport strings. Always call normalize_sport() before passing
    sport to pipeline functions that use this function.
    """
    normalized = sport.lower().strip() if sport else ""
    return SPORTS.get(normalized, {}).get("rules", {})
