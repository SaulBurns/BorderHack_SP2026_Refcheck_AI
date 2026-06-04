from rules.basketball_rules import BASKETBALL_RULES

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
        "rules": {},
    },
    "lacrosse": {
        "display_name": "Lacrosse",
        "rules": {},
    },
}

SUPPORTED_SPORTS: frozenset[str] = frozenset(SPORTS)


def normalize_sport(sport: str) -> str:
    """Lowercase and strip the value; return 'basketball' for unrecognized sports."""
    normalized = sport.lower().strip() if sport else ""
    return normalized if normalized in SPORTS else "basketball"


def get_rules_for_sport(sport: str) -> dict:
    """Return the rules dict for a sport. Empty dict for unimplemented sports."""
    normalized = sport.lower().strip() if sport else ""
    if normalized not in SPORTS:
        return {}
    return SPORTS[normalized].get("rules", {})
