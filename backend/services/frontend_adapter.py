from hashlib import sha256
from time import perf_counter


_START_TIME = perf_counter()


def _frontend_verdict(verdict: str) -> str:
    mapping = {
        "Fair Call": "fair_call",
        "Bad Call": "bad_call",
        "Inconclusive": "inconclusive",
    }
    return mapping.get(verdict, "inconclusive")


def _frontend_confidence(confidence: str) -> float:
    mapping = {
        "High": 0.88,
        "Medium": 0.68,
        "Low": 0.42,
    }
    return mapping.get(confidence, 0.5)


def _clip_id(result: dict) -> str:
    metadata = result.get("video_metadata") or {}
    source = f"{metadata.get('stored_path', '')}:{metadata.get('size_bytes', 0)}"
    return sha256(source.encode("utf-8")).hexdigest()[:12]


def to_frontend_response(result: dict) -> dict:
    verdict = _frontend_verdict(result["verdict"])
    confidence = _frontend_confidence(result["confidence"])
    rule_id = result["call_type"].upper().replace(" / ", "_").replace(" ", "_")

    adjudicator_a = {
        "verdict": verdict,
        "confidence": confidence,
        "primary_rule_id": rule_id,
        "reasoning": result["reasoning"],
        "flags": result["evidence"],
    }

    return {
        "clip_id": _clip_id(result),
        "verdict": {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": result["reasoning"],
            "cited_rule": {
                "rule_id": rule_id,
                "section_title": result["rule_applied"],
                "text": result["evidence"][1] if len(result["evidence"]) > 1 else "",
                "page_number": 1,
                "similarity_score": 0.84,
            },
            "perception": {
                "sport": "basketball",
                "event_type": result["call_type"],
                "summary": result["evidence"][2] if len(result["evidence"]) > 2 else "",
                "players_involved": [
                    {
                        "role": "offense",
                        "jersey_color": None,
                        "position_description": "Ball handler near the point of contact",
                        "body_state": "Driving through the play",
                    },
                    {
                        "role": "defense",
                        "jersey_color": None,
                        "position_description": "Defender contesting the play",
                        "body_state": "Establishing or adjusting guarding position",
                    },
                ],
                "contact_detected": True,
                "ball_visible": True,
                "moment_of_interest_seconds": 4.2,
                "visual_quality": "partial",
                "perception_confidence": confidence,
                "notes": "Mock multimodal analysis. Real frame analysis can replace this service later.",
            },
            "adjudicator_a": adjudicator_a,
            "adjudicator_b": {
                **adjudicator_a,
                "confidence": max(0.25, confidence - 0.08),
                "flags": ["Second mock review agreed with the primary rule comparison."],
            },
            "reconciliation_note": (
                "Both mock adjudicators compared the submitted call details against the "
                "selected basketball rule and returned a stable demo verdict."
            ),
            "processing_time_seconds": round(perf_counter() - _START_TIME, 1),
        },
    }
