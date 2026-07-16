"""Canned mock analysis result (Sprint 7 extraction).

The demo-safe, network-free result the pipeline returns when AI_PROVIDER is
mock or a real run degrades. Shape mirrors the real response. Unchanged."""

from __future__ import annotations

from fastapi import UploadFile

from services.mock_analyzer import analyze_clip as mock_analyze_clip
from services.text_utils import rule_id_from_call_type
from services.verdicts import normalize_verdict as _frontend_verdict


def _mock_ai_result(
    file: UploadFile,
    sport: str,
    level_of_play: str,
    league: str,
    original_call: str,
    referee_name: str,
    video_metadata: dict | None,
    fallback_reason: str | None,
) -> dict:
    result = mock_analyze_clip(
        file=file,
        sport=sport,
        level_of_play=level_of_play,
        league=league,
        original_call=original_call,
        referee_name=referee_name,
        video_metadata=video_metadata,
    )
    confidence = {"High": 0.88, "Medium": 0.68, "Low": 0.42}.get(
        result["confidence"], 0.5
    )
    return {
        "provider_used": "mock",
        "fallback_reason": fallback_reason,
        "retrieval_query": "",
        "retrieved_rules": [
            {
                "rule_id": rule_id_from_call_type(result["call_type"]),
                "section_title": result["rule_applied"],
                "text": result["evidence"][1],
                "page_number": 1,
                "call_type": result["call_type"],
            }
        ],
        "perception": {
            "sport": sport,
            "event_type": result["call_type"],
            "summary": result["evidence"][2],
            "players_involved": [
                {
                    "role": "offense",
                    "jersey_color": None,
                    "position_description": "Ball handler near the point of contact",
                    "court_zone": "paint_lane",
                    "body_state": "Driving through the play",
                },
                {
                    "role": "defense",
                    "jersey_color": None,
                    "position_description": "Defender contesting the play",
                    "court_zone": "paint_lane",
                    "body_state": "Establishing or adjusting guarding position",
                },
            ],
            "contact_detected": True,
            "contact_location": "unclear",
            "ball_visible": True,
            "ball_state": "unclear",
            "offensive_control_status": "unclear",
            "defender_status": {
                "primary_or_secondary": "unclear",
                "legal_guarding_position": "unclear",
                "feet_set_before_contact": False,
                "moving_direction": "unclear",
                "inside_restricted_area": False,
            },
            "court_geometry": {
                "key_zone": "paint_lane",
                "restricted_area_arc_visible": False,
                "defender_feet_visible": False,
                "basket_visible": False,
            },
            "frame_observations": [
                {
                    "frame_index": 1,
                    "approx_time_seconds": 4.2,
                    "observation": "Mock fallback cannot inspect exact court geometry.",
                }
            ],
            "moment_of_interest_seconds": 4.2,
            "impact_zone": {
                "x_percent": 50,
                "y_percent": 50,
                "radius_percent": 14,
                "label": "Estimated contact area",
            },
            "visual_quality": "partial",
            "perception_confidence": confidence,
            "notes": fallback_reason or "Mock fallback used for demo stability.",
        },
        "adjudicator_a": {
            "verdict": _frontend_verdict(result["verdict"]),
            "confidence": confidence,
            "primary_rule_id": rule_id_from_call_type(result["call_type"]),
            "supporting_rule_ids": [],
            "reasoning": result["reasoning"],
            "flags": [fallback_reason or "Mock fallback used for demo stability."],
        },
        "adjudicator_b": {
            "verdict": _frontend_verdict(result["verdict"]),
            "confidence": max(0.25, confidence - 0.06),
            "primary_rule_id": rule_id_from_call_type(result["call_type"]),
            "supporting_rule_ids": [],
            "reasoning": result["reasoning"],
            "flags": [fallback_reason or "Mock fallback used for demo stability."],
        },
    }
