from fastapi import UploadFile

from rules.basketball_rules import BASKETBALL_RULES, DEFAULT_BASKETBALL_RULE


def _clean(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    return value.strip() or fallback


def _mock_verdict(original_call: str) -> tuple[str, str]:
    call = original_call.lower()

    if not call:
        return "Inconclusive", "Medium"
    if any(term in call for term in ["charge", "offensive", "fair", "correct"]):
        return "Fair Call", "High"
    if any(term in call for term in ["block", "blocking", "bad", "missed"]):
        return "Bad Call", "Medium"
    return "Inconclusive", "Low"


def _select_rule(original_call: str) -> dict:
    call = original_call.lower()

    if any(term in call for term in ["shoot", "shooting", "arm", "free throw"]):
        return BASKETBALL_RULES["shooting_contact"]
    if any(term in call for term in ["out", "boundary", "sideline", "baseline"]):
        return BASKETBALL_RULES["out_of_bounds"]
    if any(term in call for term in ["travel", "steps", "pivot"]):
        return BASKETBALL_RULES["travel"]
    if any(term in call for term in ["goaltend", "basket interference", "cylinder"]):
        return BASKETBALL_RULES["goaltending"]
    return DEFAULT_BASKETBALL_RULE


def analyze_clip(
    file: UploadFile,
    sport: str,
    level_of_play: str | None = None,
    league: str | None = None,
    original_call: str | None = None,
    referee_name: str | None = None,
    video_metadata: dict | None = None,
) -> dict:
    normalized_sport = _clean(sport, "Basketball")
    normalized_level = _clean(level_of_play)
    normalized_league = _clean(league)
    normalized_original_call = _clean(original_call)
    normalized_referee_name = _clean(referee_name)

    rule = _select_rule(normalized_original_call)
    verdict, confidence = _mock_verdict(normalized_original_call)

    if verdict == "Fair Call":
        reasoning = (
            "The mock review supports the original call. The defender appears to have "
            "established position before contact, and the offensive player initiates "
            "the main body contact through the torso."
        )
    elif verdict == "Bad Call":
        reasoning = (
            "The mock review would overturn the original call. The defender appears to "
            "slide laterally into the ball handler's path before contact, which points "
            "toward blocking responsibility."
        )
    else:
        reasoning = (
            "The mock review cannot make a strong ruling from the submitted details alone. "
            "A real model would inspect frames around the point of contact, player position, "
            "and timing before assigning a final verdict."
        )

    return {
        "verdict": verdict,
        "confidence": confidence,
        "sport": normalized_sport,
        "level_of_play": normalized_level,
        "league": normalized_league,
        "original_call": normalized_original_call,
        "referee_name": normalized_referee_name,
        "analysis_mode": "mock_multimodal",
        "call_type": rule["call_type"],
        "rule_applied": rule["rule_applied"],
        "reasoning": reasoning,
        "video_metadata": video_metadata or {
            "filename": file.filename or "uploaded clip",
            "content_type": file.content_type or "unknown",
            "size_bytes": 0,
        },
        "evidence": [
            f"Received and stored video file: {file.filename or 'uploaded clip'}",
            rule["summary"],
            "Mock analysis focused on defender position, contact timing, and who initiated contact.",
        ],
    }
