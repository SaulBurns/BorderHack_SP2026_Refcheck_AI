import base64
import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import UploadFile

from rules.basketball_rules import BASKETBALL_RULES, DEFAULT_BASKETBALL_RULE
from services.mock_analyzer import analyze_clip as mock_analyze_clip

try:
    import certifi
except ImportError:
    certifi = None


FRAME_DIR = Path(__file__).resolve().parents[1] / "uploads" / "frames"
DEFAULT_MODEL_BY_PROVIDER = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4.1-mini",
}

PERCEPTION_SYSTEM_PROMPT = """
You are a sports video analyst specializing in basketball officiating review.

You will receive a sequence of evenly-spaced frames from a short basketball clip. Your job is to describe what you observe in structured form. You are NOT issuing a verdict. A separate agent will rule on the call. Your role is to be the most accurate possible eyes for the system.

OBSERVATION GUIDELINES:

Players: Identify offensive and defensive players involved in the key moment. Describe their jersey color, spatial position on the court, and body state at the moment of contact or interest. Body state is critical: stationary, moving laterally, jumping, descending, falling, airborne, planted, sliding.

Contact: Did contact occur? If yes, which players, and was it at the torso, arm, lower body, or unclear? Was the contact incidental or significant?

Ball: Where is the ball through the clip? Is the offensive player gathering it, dribbling, in upward shooting motion, releasing, or in flight?

Visual quality: Honestly assess the camera angle. Is the key moment clearly visible, partially obscured, blocked by another player, or unusable?

UNCERTAINTY DISCIPLINE:

Be honest. If a frame is blurry, an angle is wrong, or you cannot tell what happened, say so and lower perception_confidence.

OUTPUT FORMAT:
Output ONLY valid JSON. No prose, no markdown fences.
{
  "sport": "basketball",
  "event_type": "possible_blocking_foul | possible_charge | possible_travel | possible_goaltending | possible_offensive_foul | out_of_bounds | shot_clock_violation | three_seconds_violation | unclear",
  "summary": "2 to 4 sentences describing what happens in plain English",
  "players_involved": [
    {
      "role": "offense | defense | unclear",
      "jersey_color": "color string or null",
      "position_description": "where they are on the court",
      "body_state": "motion state at moment of interest"
    }
  ],
  "contact_detected": true,
  "contact_location": "torso | arm | lower_body | unclear | none",
  "ball_visible": true,
  "ball_state": "gathered | dribbling | upward_motion | released | in_flight | unclear",
  "moment_of_interest_seconds": 0.0,
  "impact_zone": {
    "x_percent": 50,
    "y_percent": 50,
    "radius_percent": 12,
    "label": "contact point or decisive action"
  },
  "visual_quality": "clear | partial | obstructed | poor",
  "perception_confidence": 0.0,
  "notes": "optional caveats"
}

Impact zone should be normalized to the frame: x_percent and y_percent range from 0 to 100. Use it to identify the visible contact point, foot placement, ball release, boundary touch, or other decisive visual region. If the exact point is unclear, estimate the most relevant area and lower confidence.
""".strip()

RETRIEVAL_SYSTEM_PROMPT = """
You convert basketball play descriptions into precise rulebook search queries.

Your output will be used to retrieve relevant rules. The search works best on concise, noun-heavy queries that mirror rulebook language, not narrative prose.

QUERY CRAFTING RULES:
1. Output ONLY the search query as plain text. No preamble, no quotes, no markdown.
2. 5 to 15 words.
3. Focus on nouns and rule-relevant concepts: positions, body states, contact, timing, ball state, court geometry.
4. Avoid narrative connectives like then, after, while, when.
5. Use canonical rulebook terminology: legal guarding position, verticality, established position, airborne shooter, incidental contact, continuation, cylinder, gather, pivot foot, downward flight, boundary line.
""".strip()

ADJUDICATOR_BASE_SYSTEM_PROMPT = """
You are an experienced basketball officiating reviewer with deep knowledge of the NBA rulebook.

You will be given:
1. A structured description of what happened in a clip, produced by a perception agent
2. The most relevant rules, retrieved by rulebook search
3. Optionally, what the on-court referee originally called

Your job is to issue a verdict on whether the original officiating call was correct.

VALID VERDICTS:
- "fair_call": the original call was consistent with the rules, given the evidence
- "bad_call": the original call was inconsistent with the rules, given the evidence
- "inconclusive": the visual evidence is insufficient to render a confident verdict

CITATION DISCIPLINE:
You must cite at least one rule by its rule_id from the retrieved rules. Do not invent rule IDs. Your reasoning must explicitly connect the play details to the cited rule text.

UNCERTAINTY DISCIPLINE:
If perception_confidence is low (<0.5) or visual_quality is "obstructed" or "poor", lean toward inconclusive. If the retrieved rules do not cover the situation, return inconclusive with a flag.

OUTPUT FORMAT:
Output ONLY valid JSON. No prose, no markdown fences.
{
  "verdict": "fair_call | bad_call | inconclusive",
  "confidence": 0.0,
  "primary_rule_id": "rule_id from retrieved rules or null",
  "supporting_rule_ids": ["additional rule_ids"],
  "reasoning": "2 to 4 sentences citing the primary rule text and applying evidence",
  "flags": ["concern strings"]
}
""".strip()

CONSERVATIVE_FRAMING = """
REASONING POSTURE - CONSERVATIVE:

The on-court referee saw the play live, in full speed, from their position. Give the original call the benefit of the doubt unless the rules and perception evidence clearly indicate otherwise. This does not mean defending bad calls.
""".strip()

SKEPTICAL_FRAMING = """
REASONING POSTURE - SKEPTICAL:

You are an independent reviewer. Do not defer to the original call by default. Examine the evidence and rules on their own merits. If the evidence supports a different interpretation than the original call, say so.
""".strip()


def _clean(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    return value.strip() or fallback


def _clip_id(video_metadata: dict | None) -> str:
    metadata = video_metadata or {}
    source = f"{metadata.get('stored_path', '')}:{metadata.get('size_bytes', 0)}"
    return sha256(source.encode("utf-8")).hexdigest()[:12]


def _frontend_verdict(value: str | None) -> str:
    normalized = (value or "").lower().strip().replace(" ", "_")
    mapping = {
        "fair": "fair_call",
        "fair_call": "fair_call",
        "good_call": "fair_call",
        "correct_call": "fair_call",
        "bad": "bad_call",
        "bad_call": "bad_call",
        "missed_call": "bad_call",
        "incorrect_call": "bad_call",
        "inconclusive": "inconclusive",
    }
    return mapping.get(normalized, "inconclusive")


def _safe_float(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, number))


def _extract_frames(video_path: str | None, clip_id: str, max_frames: int = 10) -> list[Path]:
    if not video_path:
        return []

    source = Path(video_path)
    if not source.exists():
        return []

    output_dir = FRAME_DIR / clip_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%03d.jpg")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        f"fps=1,scale=768:-1",
        "-frames:v",
        str(max_frames),
        output_pattern,
    ]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=45,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    return sorted(output_dir.glob("frame_*.jpg"))[:max_frames]


def _image_blocks_for_anthropic(frame_paths: list[Path]) -> list[dict]:
    blocks = []
    for path in frame_paths:
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": data,
                },
            }
        )
    return blocks


def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    context = ssl.create_default_context(cafile=certifi.where()) if certifi else None

    try:
        with urllib.request.urlopen(request, timeout=90, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AI provider HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"AI provider request failed: {exc.reason}") from exc


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _anthropic_text_from_response(response: dict) -> str:
    return "".join(
        block.get("text", "")
        for block in response.get("content", [])
        if block.get("type") == "text"
    )


def _call_anthropic_messages(
    *,
    system_prompt: str,
    user_content: str | list[dict],
    temperature: float,
    max_tokens: int = 1200,
) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    model = os.getenv("AI_MODEL") or DEFAULT_MODEL_BY_PROVIDER["anthropic"]
    content = user_content
    if isinstance(user_content, str):
        content = [{"type": "text", "text": user_content}]

    payload = {
        "model": model,
        "system": system_prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": content}],
    }
    response = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        payload,
    )
    return _anthropic_text_from_response(response)


def _perception_agent(frame_paths: list[Path], original_call: str) -> dict:
    context = (
        f"The on-court referee called: '{original_call}'. Use this only as context "
        "for what to focus on. Do not let it bias your perception of what happened."
        if original_call
        else "No original call was provided. Describe what you observe."
    )
    user_blocks = _image_blocks_for_anthropic(frame_paths)
    user_blocks.append(
        {
            "type": "text",
            "text": (
                f"Analyze these {len(frame_paths)} frames from a basketball clip.\n\n"
                f"{context}\n\nReturn your structured observation as JSON."
            ),
        }
    )
    return _extract_json(
        _call_anthropic_messages(
            system_prompt=PERCEPTION_SYSTEM_PROMPT,
            user_content=user_blocks,
            temperature=0,
            max_tokens=1600,
        )
    )


def _retrieval_agent(perception: dict) -> str:
    prompt = f"""
Event type: {perception.get("event_type", "unclear")}
Summary: {perception.get("summary", "")}
Contact detected: {perception.get("contact_detected", False)}
Contact location: {perception.get("contact_location", "unclear")}
Ball state: {perception.get("ball_state", "unclear")}

Write the rulebook search query.
""".strip()
    return _call_anthropic_messages(
        system_prompt=RETRIEVAL_SYSTEM_PROMPT,
        user_content=prompt,
        temperature=0,
        max_tokens=80,
    ).strip().strip('"')


def _rule_records() -> list[dict]:
    records = []
    for key, rule in BASKETBALL_RULES.items():
        records.append(
            {
                "rule_id": key.upper(),
                "section_title": rule["rule_applied"],
                "text": rule["summary"],
                "page_number": rule.get("page_number", 1),
                "call_type": rule["call_type"],
            }
        )
    return records


def _retrieve_rules(query: str, perception: dict, limit: int = 5) -> list[dict]:
    haystack = f"{query} {perception.get('event_type', '')} {perception.get('summary', '')}".lower()
    scored = []
    for rule in _rule_records():
        rule_text = f"{rule['rule_id']} {rule['section_title']} {rule['text']} {rule['call_type']}".lower()
        score = sum(1 for term in haystack.split() if term in rule_text)
        if rule["rule_id"] == "BLOCK_CHARGE" and any(
            term in haystack for term in ["charge", "blocking", "guarding", "lateral", "torso"]
        ):
            score += 6
        if rule["rule_id"] == "SHOOTING_CONTACT" and any(
            term in haystack for term in ["shoot", "shooter", "airborne", "arm", "landing", "verticality"]
        ):
            score += 6
        if rule["rule_id"] == "TRAVEL" and any(
            term in haystack for term in ["travel", "pivot", "gather", "steps", "dribble"]
        ):
            score += 6
        if rule["rule_id"] == "OUT_OF_BOUNDS" and any(
            term in haystack for term in ["out", "boundary", "sideline", "baseline", "last"]
        ):
            score += 6
        if rule["rule_id"] == "GOALTENDING" and any(
            term in haystack for term in ["goaltend", "downward", "cylinder", "rim", "interference"]
        ):
            score += 6
        scored.append((score, rule))

    ranked = [rule for _, rule in sorted(scored, key=lambda item: item[0], reverse=True)]
    return ranked[:limit] or [_rule_records()[0]]


def _rules_text(rules: list[dict]) -> str:
    return "\n\n".join(
        f"[{rule['rule_id']} | page {rule['page_number']}]\n"
        f"{rule['section_title']}\n"
        f"{rule['text']}"
        for rule in rules
    )


def _adjudicator_agent(
    *,
    perception: dict,
    rules: list[dict],
    original_call: str,
    framing: str,
    temperature: float,
) -> dict:
    original_call_line = (
        f"'{original_call}'"
        if original_call
        else "(not provided - judge whether the play was correctly officiated assuming the on-court call was made)"
    )
    prompt = f"""
Original call: {original_call_line}

PERCEPTION OUTPUT:
{json.dumps(perception, indent=2)}

RETRIEVED RULES:
{_rules_text(rules)}

Issue your verdict as JSON.
""".strip()
    return _extract_json(
        _call_anthropic_messages(
            system_prompt=f"{ADJUDICATOR_BASE_SYSTEM_PROMPT}\n\n{framing}",
            user_content=prompt,
            temperature=temperature,
            max_tokens=1200,
        )
    )


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
        "retrieval_query": "",
        "retrieved_rules": [
            {
                "rule_id": result["call_type"].upper().replace(" / ", "_").replace(" ", "_"),
                "section_title": result["rule_applied"],
                "text": result["evidence"][1],
                "page_number": 1,
                "call_type": result["call_type"],
            }
        ],
        "perception": {
            "sport": "basketball",
            "event_type": result["call_type"],
            "summary": result["evidence"][2],
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
            "contact_location": "unclear",
            "ball_visible": True,
            "ball_state": "unclear",
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
            "primary_rule_id": result["call_type"].upper().replace(" / ", "_").replace(" ", "_"),
            "supporting_rule_ids": [],
            "reasoning": result["reasoning"],
            "flags": [fallback_reason or "Mock fallback used for demo stability."],
        },
        "adjudicator_b": {
            "verdict": _frontend_verdict(result["verdict"]),
            "confidence": max(0.25, confidence - 0.06),
            "primary_rule_id": result["call_type"].upper().replace(" / ", "_").replace(" ", "_"),
            "supporting_rule_ids": [],
            "reasoning": result["reasoning"],
            "flags": [fallback_reason or "Mock fallback used for demo stability."],
        },
    }


def _run_four_agent_pipeline(
    *,
    frame_paths: list[Path],
    file: UploadFile,
    sport: str,
    level_of_play: str,
    league: str,
    original_call: str,
    referee_name: str,
    video_metadata: dict | None,
) -> dict:
    provider = _clean(os.getenv("AI_PROVIDER"), "mock").lower()

    if provider == "mock":
        return _mock_ai_result(
            file,
            sport,
            level_of_play,
            league,
            original_call,
            referee_name,
            video_metadata,
            "AI_PROVIDER is set to mock.",
        )

    if provider != "anthropic":
        return _mock_ai_result(
            file,
            sport,
            level_of_play,
            league,
            original_call,
            referee_name,
            video_metadata,
            "The four-agent pipeline currently supports AI_PROVIDER=anthropic.",
        )

    if not frame_paths:
        return _mock_ai_result(
            file,
            sport,
            level_of_play,
            league,
            original_call,
            referee_name,
            video_metadata,
            "Frame extraction failed or ffmpeg is unavailable.",
        )

    try:
        perception = _perception_agent(frame_paths, original_call)
        retrieval_query = _retrieval_agent(perception)
        retrieved_rules = _retrieve_rules(retrieval_query, perception)
        adjudicator_a = _adjudicator_agent(
            perception=perception,
            rules=retrieved_rules,
            original_call=original_call,
            framing=CONSERVATIVE_FRAMING,
            temperature=0.2,
        )
        adjudicator_b = _adjudicator_agent(
            perception=perception,
            rules=retrieved_rules,
            original_call=original_call,
            framing=SKEPTICAL_FRAMING,
            temperature=0.7,
        )
        return {
            "provider_used": "anthropic_four_agent",
            "retrieval_query": retrieval_query,
            "retrieved_rules": retrieved_rules,
            "perception": perception,
            "adjudicator_a": adjudicator_a,
            "adjudicator_b": adjudicator_b,
        }
    except Exception as exc:
        return _mock_ai_result(
            file,
            sport,
            level_of_play,
            league,
            original_call,
            referee_name,
            video_metadata,
            str(exc),
        )


def _rule_by_id(rule_id: str | None, rules: list[dict]) -> dict:
    if rule_id:
        normalized = rule_id.upper()
        for rule in rules:
            if rule["rule_id"].upper() == normalized:
                return rule
    return rules[0] if rules else {
        "rule_id": "BLOCK_CHARGE",
        "section_title": DEFAULT_BASKETBALL_RULE["rule_applied"],
        "text": DEFAULT_BASKETBALL_RULE["summary"],
        "page_number": 1,
        "call_type": DEFAULT_BASKETBALL_RULE["call_type"],
    }


def _reconcile(adjudicator_a: dict, adjudicator_b: dict, perception: dict) -> tuple[str, float, str]:
    verdict_a = _frontend_verdict(adjudicator_a.get("verdict"))
    verdict_b = _frontend_verdict(adjudicator_b.get("verdict"))
    confidence_a = _safe_float(adjudicator_a.get("confidence"), 0.5)
    confidence_b = _safe_float(adjudicator_b.get("confidence"), 0.5)
    perception_confidence = _safe_float(perception.get("perception_confidence"), 0.5)
    visual_quality = str(perception.get("visual_quality", "partial")).lower()

    if visual_quality in {"obstructed", "poor"} or perception_confidence < 0.45:
        return (
            "inconclusive",
            min(confidence_a, confidence_b, perception_confidence),
            "The adjudicators were constrained by weak visual evidence, so the system reports the play as inconclusive.",
        )

    if verdict_a == verdict_b:
        return (
            verdict_a,
            round((confidence_a + confidence_b + perception_confidence) / 3, 2),
            "Both adjudicators reached the same verdict from different review postures, increasing confidence in the final call.",
        )

    return (
        "inconclusive",
        round(min(confidence_a, confidence_b, perception_confidence), 2),
        "The conservative and skeptical adjudicators disagreed, which signals that the clip does not support a confident final verdict.",
    )


def _frontend_perception(perception: dict, provider_used: str, retrieval_query: str) -> dict:
    return {
        "sport": "basketball",
        "event_type": str(perception.get("event_type") or "unclear"),
        "summary": str(perception.get("summary") or "The perception agent reviewed the submitted basketball play."),
        "players_involved": perception.get("players_involved")
        or [
            {
                "role": "unclear",
                "jersey_color": None,
                "position_description": "Player positions were not clear enough to label.",
                "body_state": "Unclear",
            }
        ],
        "contact_detected": bool(perception.get("contact_detected", False)),
        "contact_location": str(perception.get("contact_location") or "unclear"),
        "ball_visible": bool(perception.get("ball_visible", False)),
        "ball_state": str(perception.get("ball_state") or "unclear"),
        "moment_of_interest_seconds": perception.get("moment_of_interest_seconds"),
        "impact_zone": perception.get("impact_zone")
        or {
            "x_percent": 50,
            "y_percent": 50,
            "radius_percent": 14,
            "label": "Estimated impact zone",
        },
        "visual_quality": str(perception.get("visual_quality") or "partial"),
        "perception_confidence": _safe_float(perception.get("perception_confidence"), 0.5),
        "notes": (
            f"analysis_provider={provider_used}; "
            f"retrieval_query={retrieval_query}; "
            f"contact_location={perception.get('contact_location', 'unclear')}; "
            f"ball_state={perception.get('ball_state', 'unclear')}; "
            f"notes={perception.get('notes', '')}"
        ),
    }


def _frontend_adjudicator(adjudicator: dict, fallback_rule: dict) -> dict:
    flags = adjudicator.get("flags") or []
    if not isinstance(flags, list):
        flags = [str(flags)]

    return {
        "verdict": _frontend_verdict(adjudicator.get("verdict")),
        "confidence": _safe_float(adjudicator.get("confidence"), 0.5),
        "primary_rule_id": adjudicator.get("primary_rule_id") or fallback_rule["rule_id"],
        "reasoning": str(
            adjudicator.get("reasoning")
            or "The adjudicator could not make a confident ruling from the available evidence."
        ),
        "flags": flags,
    }


def _key_moment_payload(frame_paths: list[Path], perception: dict, clip_id: str, reasoning: str) -> dict | None:
    if not frame_paths:
        return None

    moment_seconds = perception.get("moment_of_interest_seconds")
    try:
        frame_index = round(float(moment_seconds))
    except (TypeError, ValueError):
        frame_index = len(frame_paths) // 2

    frame_index = max(0, min(len(frame_paths) - 1, frame_index))
    frame_path = frame_paths[frame_index]

    return {
        "frame_url": f"/api/frames/{clip_id}/{frame_path.name}",
        "frame_number": frame_index + 1,
        "approximate_seconds": moment_seconds,
        "title": "Key Moment Frame",
        "explanation": (
            perception.get("summary")
            or reasoning
            or "This frame is closest to the moment the AI identified as decisive."
        ),
    }


def _build_response(
    *,
    agent_result: dict,
    clip_id: str,
    frame_paths: list[Path],
    video_metadata: dict | None,
    processing_time_seconds: float,
) -> dict:
    perception = agent_result["perception"]
    retrieved_rules = agent_result["retrieved_rules"]
    provider_used = agent_result["provider_used"]
    retrieval_query = agent_result.get("retrieval_query", "")
    adjudicator_a_raw = agent_result["adjudicator_a"]
    adjudicator_b_raw = agent_result["adjudicator_b"]
    final_verdict, final_confidence, reconciliation_note = _reconcile(
        adjudicator_a_raw, adjudicator_b_raw, perception
    )
    primary_rule = _rule_by_id(
        adjudicator_a_raw.get("primary_rule_id") or adjudicator_b_raw.get("primary_rule_id"),
        retrieved_rules,
    )

    adjudicator_a = _frontend_adjudicator(adjudicator_a_raw, primary_rule)
    adjudicator_b = _frontend_adjudicator(adjudicator_b_raw, primary_rule)
    reasoning = (
        adjudicator_a["reasoning"]
        if _frontend_verdict(adjudicator_a_raw.get("verdict")) == final_verdict
        else adjudicator_b["reasoning"]
    )
    if final_verdict == "inconclusive" and adjudicator_a["verdict"] != adjudicator_b["verdict"]:
        reasoning = reconciliation_note

    key_moment = _key_moment_payload(frame_paths, perception, clip_id, reasoning)

    response = {
        "clip_id": clip_id,
        "verdict": {
            "verdict": final_verdict,
            "confidence": final_confidence,
            "reasoning": reasoning,
            "cited_rule": {
                "rule_id": primary_rule["rule_id"],
                "section_title": primary_rule["section_title"],
                "text": primary_rule["text"],
                "page_number": primary_rule.get("page_number", 1),
                "similarity_score": 0.86,
            },
            "perception": _frontend_perception(perception, provider_used, retrieval_query),
            "adjudicator_a": adjudicator_a,
            "adjudicator_b": adjudicator_b,
            "reconciliation_note": reconciliation_note,
            "processing_time_seconds": round(processing_time_seconds, 1),
        },
    }
    if key_moment:
        response["key_moment"] = key_moment
    stored_path = (video_metadata or {}).get("stored_path")
    if stored_path:
        response["clip_url"] = f"/api/clips/{Path(stored_path).name}"
    return response


def analyze_clip(
    file: UploadFile,
    sport: str,
    level_of_play: str | None = None,
    league: str | None = None,
    original_call: str | None = None,
    referee_name: str | None = None,
    video_metadata: dict | None = None,
) -> dict:
    start = perf_counter()
    normalized_sport = _clean(sport, "basketball")
    normalized_level = _clean(level_of_play)
    normalized_league = _clean(league)
    normalized_original_call = _clean(original_call)
    normalized_referee_name = _clean(referee_name)
    clip_id = _clip_id(video_metadata)
    frame_paths = _extract_frames((video_metadata or {}).get("stored_path"), clip_id)

    agent_result = _run_four_agent_pipeline(
        frame_paths=frame_paths,
        file=file,
        sport=normalized_sport,
        level_of_play=normalized_level,
        league=normalized_league,
        original_call=normalized_original_call,
        referee_name=normalized_referee_name,
        video_metadata=video_metadata,
    )

    return _build_response(
        agent_result=agent_result,
        clip_id=clip_id,
        frame_paths=frame_paths,
        video_metadata=video_metadata,
        processing_time_seconds=perf_counter() - start,
    )
