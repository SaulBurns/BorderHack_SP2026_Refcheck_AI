import copy
import json
import logging
import os
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import UploadFile

from services import config
from services.ai import get_provider, image_part, text_part
from services.ai.errors import ProviderError
from services.ai.provider import AIProvider, MessageContent
from services.analysis.calibration import calibrate_confidence
from services.analysis.contracts import AgentResult, RuleRecord
from services.analysis.diagnostics import _diagnostics_payload
from services.analysis.frames import FRAME_DIR, _extract_frames
from services.analysis.mock_result import _mock_ai_result
from services.analysis.prompts import (
    CONSERVATIVE_FRAMING,
    SKEPTICAL_FRAMING,
    _get_adjudicator_prompt,
    _get_perception_prompt,
)
from services.analysis.rule_corpus import _rule_records, _rules_text
from services.analysis.response_models import AdjudicatorResponse, PerceptionResponse
from services.ai.reliability import call_with_retry
from pydantic import BaseModel, ValidationError
from services.detectors import RawDetections, get_detector
from services.extractors import get_extractor
from sports import get_sport
from services.perception_schema import SCHEMA_VERSION
from services.text_utils import clean as _clean
from services.verdicts import normalize_verdict as _frontend_verdict

# `_extract_frames`, `_rule_records`, `_rules_text`, `_mock_ai_result`,
# `_diagnostics_payload`, and the prompt helpers are imported (not defined) here
# so the orchestration functions below call them by bare name — which keeps every
# `from services.ai_analyzer import ...` path and `monkeypatch.setattr(ai, ...)`
# seam working exactly as before the Sprint 7 split.

logger = logging.getLogger("refcheck.ai")


# ---------------------------------------------------------------------------
# Provider-instance cache (Sprint 6 perf).
# `get_provider()` re-reads AI_PROVIDER and instantiates a fresh provider object
# on every call; the pipeline calls it ~5x per analysis (1 pipeline check + 4
# agent turns). We cache the resolved instance keyed on the resolved provider
# name, so repeated calls within a process reuse it. A changed AI_PROVIDER (e.g.
# the evaluation CLI swapping providers between runs) produces a different key and
# still re-resolves — behavior is identical, only object churn is removed.
# Providers read their secrets/model lazily inside send_messages, so a cached
# instance never goes stale on an ANTHROPIC_API_KEY / AI_MODEL change.
# ---------------------------------------------------------------------------

_PROVIDER_CACHE: dict[str, AIProvider] = {}


def _provider_key() -> str:
    return config.resolved_provider()


def _active_provider() -> AIProvider:
    key = _provider_key()
    provider = _PROVIDER_CACHE.get(key)
    if provider is None:
        provider = get_provider()
        _PROVIDER_CACHE[key] = provider
    return provider


def _reset_provider_cache() -> None:
    """Clear the provider-instance cache (used by tests and the benchmark)."""
    _PROVIDER_CACHE.clear()


# ---------------------------------------------------------------------------
# Analysis result cache (Sprint 6 perf) — OPT-IN, default OFF.
# Within a single analysis the four agents are all distinct calls (no duplicate
# Claude requests exist to remove). Duplicate requests arise *across* analyses of
# the same clip: demo suites, evaluation benchmarks re-running a dataset, or a
# user resubmitting a clip. When ANALYSIS_CACHE is truthy, the fully-built
# response is memoized by (clip identity + inputs + provider + model), so a repeat
# analysis returns instantly with zero model calls. Default OFF keeps the API
# byte-for-byte identical to today (adjudicator B runs at temperature 0.7, so
# re-running is intentionally non-deterministic unless caching is enabled).
# ---------------------------------------------------------------------------

_RESULT_CACHE: "OrderedDict[str, dict]" = OrderedDict()
_RESULT_CACHE_MAX = 128


def _analysis_cache_enabled() -> bool:
    return config.env_flag(config.ANALYSIS_CACHE_ENV)


def _analysis_cache_key(
    clip_id: str,
    sport: str,
    level: str,
    league: str,
    original_call: str,
    referee: str,
) -> str:
    raw = "|".join(
        [clip_id, sport, level, league, original_call, referee, _provider_key(), os.getenv(config.AI_MODEL_ENV, "")]
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict | None:
    cached = _RESULT_CACHE.get(key)
    if cached is None:
        return None
    _RESULT_CACHE.move_to_end(key)
    # Deep copy so a caller mutating the response never corrupts the cached entry.
    return copy.deepcopy(cached)


def _cache_put(key: str, response: dict) -> None:
    _RESULT_CACHE[key] = copy.deepcopy(response)
    _RESULT_CACHE.move_to_end(key)
    while len(_RESULT_CACHE) > _RESULT_CACHE_MAX:
        _RESULT_CACHE.popitem(last=False)


def _reset_result_cache() -> None:
    """Clear the analysis result cache (used by tests)."""
    _RESULT_CACHE.clear()


def _clip_id(video_metadata: dict | None) -> str:
    metadata = video_metadata or {}
    source = f"{metadata.get('stored_path', '')}:{metadata.get('size_bytes', 0)}"
    return sha256(source.encode("utf-8")).hexdigest()[:12]


def _safe_float(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, number))


class StructuredOutputError(RuntimeError):
    """Raised when a model reply fails Pydantic validation after all retries.

    Carries a descriptive message so the surrounding `_run_four_agent_pipeline`
    `except` turns it into an informative `fallback_reason` (better diagnostics).
    """

    def __init__(self, model_name: str, attempts: int, error: ValidationError | None):
        super().__init__(
            f"structured-output validation failed for {model_name} after "
            f"{attempts} attempt(s): {error}"
        )


# Appended to the user turn on a retry so the model corrects a malformed reply.
_RETRY_INSTRUCTION = (
    "Your previous reply was not valid JSON matching the required schema. Reply "
    "again with ONLY a single valid JSON object that conforms to the schema — no "
    "prose, no markdown fences, no extra text."
)


def _structured_retries() -> int:
    """How many times a validation failure is retried (env-tunable; default 1)."""
    raw = os.getenv(config.STRUCTURED_OUTPUT_RETRIES_ENV)
    if raw is None:
        return config.DEFAULT_STRUCTURED_OUTPUT_RETRIES
    try:
        return max(0, int(raw))
    except ValueError:
        return config.DEFAULT_STRUCTURED_OUTPUT_RETRIES


def _with_retry_nudge(user_content: MessageContent) -> MessageContent:
    """Append the corrective instruction to a (string or multimodal) user turn."""
    if isinstance(user_content, str):
        return f"{user_content}\n\n{_RETRY_INSTRUCTION}"
    return list(user_content) + [text_part(_RETRY_INSTRUCTION)]


def _send_messages(
    *,
    system_prompt: str,
    user_content: MessageContent,
    temperature: float,
    max_tokens: int = 1200,
    response_schema: dict | None = None,
    task: str | None = None,
) -> str:
    """Send one turn through the active AI provider and return its raw text.

    The pipeline calls only this seam; which provider answers (Anthropic, Gemini,
    mock, or a router-selected delegate) is resolved by the factory from AI_PROVIDER.
    No provider-specific code lives here. `response_schema` (Sprint 16B) is forwarded
    so the provider can request native structured output.

    Sprint 17A — provider router: `task` ("perception"/"adjudication") is resolved to
    a concrete delegate via `provider.route(task)` (a no-op returning the same provider
    unless `AI_PROVIDER=router`). The delegate is what's wrapped in `call_with_retry`,
    so single-provider behavior is unchanged and, under routing, the reliability
    diagnostics report the real provider+model that ran — never "router".

    Sprint 16D — transport reliability: the provider call is wrapped in
    `call_with_retry`, which retries **transient** failures (429/5xx/timeout/dropped
    connection) with exponential backoff and records provider-comms health. Auth /
    bad-request errors are permanent and raised immediately; validation failures are
    handled a layer up in `_send_validated`, so they are never transport-retried.

    Sprint 17C — graceful failover: if the primary provider still fails after its
    transport retries (or fails permanently, e.g. missing key / missing SDK) and a
    `PROVIDER_FALLBACK` provider is configured (and differs from the primary), the
    same turn is retried once on that fallback provider before the caller degrades to
    the mock. This makes a Gemini deployment resilient — a Gemini outage fails over to
    Anthropic — with no failover configured, behavior is exactly as before.
    """
    primary = _active_provider().route(task)
    try:
        return _call_provider(
            primary,
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=response_schema,
        )
    except ProviderError as exc:
        fallback = config.fallback_provider()
        if not fallback or fallback == primary.provider_name():
            raise
        delegate = get_provider(fallback).route(task)
        logger.warning(
            "provider %s failed (%s); failing over to %s",
            primary.provider_name(), exc, delegate.provider_name(),
        )
        return _call_provider(
            delegate,
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=response_schema,
        )


def _call_provider(
    provider: AIProvider,
    *,
    system_prompt: str,
    user_content: MessageContent,
    temperature: float,
    max_tokens: int,
    response_schema: dict | None,
) -> str:
    """One reliability-wrapped provider turn (shared by primary + failover paths)."""
    return call_with_retry(
        lambda: provider.send_messages(
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=response_schema,
        ),
        provider=provider.provider_name(),
        model=provider.model_name(),
    )


def _send_validated(
    *,
    system_prompt: str,
    user_content: MessageContent,
    temperature: float,
    model_cls: type[BaseModel],
    max_tokens: int = 1200,
    retries: int | None = None,
) -> dict:
    """Send one turn and validate the reply against `model_cls` (Sprint 16B).

    The provider is asked for native structured output (via the model's JSON
    Schema); the raw text is then validated with Pydantic's `model_validate_json`
    — a single step that parses the JSON *and* checks the schema, so there is no
    hand-rolled `json.loads` and no regex extraction anywhere. A `ValidationError`
    (malformed JSON OR missing/typed-wrong fields) is retried up to `retries` times
    with a corrective nudge appended to the user turn. **Only validation failures
    retry** — provider/network errors propagate to the caller's `except` (the mock
    fallback). Returns `model.model_dump()`, the same plain dict shape as before, so
    every downstream reader and the `/api/analyze` response are unchanged.
    """
    schema = model_cls.model_json_schema()
    # The model class is the task signal the router (Sprint 17A) selects on.
    task = config.TASK_PERCEPTION if model_cls is PerceptionResponse else config.TASK_ADJUDICATION
    attempts = (retries if retries is not None else _structured_retries()) + 1
    content = user_content
    last_error: ValidationError | None = None
    for _ in range(attempts):
        raw = _send_messages(
            system_prompt=system_prompt,
            user_content=content,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=schema,
            task=task,
        )
        try:
            return model_cls.model_validate_json(raw).model_dump()
        except ValidationError as exc:
            last_error = exc
            content = _with_retry_nudge(user_content)
    raise StructuredOutputError(model_cls.__name__, attempts, last_error)


def _perception_agent(frame_paths: list[Path], original_call: str, sport: str) -> dict:
    context = (
        f"The on-court referee called: '{original_call}'. Use this only as context "
        "for what to focus on. Do not let it bias your perception of what happened."
        if original_call
        else "No original call was provided. Describe what you observe."
    )
    user_blocks = [image_part(path) for path in frame_paths]
    user_blocks.append(
        text_part(
            f"Analyze these {len(frame_paths)} frames from a {sport} clip.\n\n"
            f"{context}\n\nReturn your structured observation as JSON."
        )
    )
    return _send_validated(
        system_prompt=_get_perception_prompt(sport),
        user_content=user_blocks,
        temperature=0,
        model_cls=PerceptionResponse,
        max_tokens=1600,
    )


def _build_adjudicator_prompt(
    *,
    perception: dict,
    rules: list[dict],
    original_call: str,
    sport_details: dict | None = None,
    tracked_evidence: dict | None = None,
) -> str:
    """Build the adjudicator user prompt.

    The user prompt is *identical* for both adjudicators — only the system
    framing and temperature differ. Building it once (Sprint 6) avoids
    serializing the perception dict, sport signals, tracked evidence and
    rulebook text twice per analysis. `rules` is the sport's *complete* rule
    corpus (Sprint 16A removed the retrieval stage), injected in full so the
    adjudicators can cite any applicable rule directly.
    """
    original_call_line = (
        f"'{original_call}'"
        if original_call
        else "(not provided - judge whether the play was correctly officiated assuming the on-court call was made)"
    )
    # Detection-derived sport signals (Phase 9). Only included when present, so
    # the claude_vision/mock path prompt is unchanged.
    sport_details_section = (
        "\n\nSPORT-SPECIFIC SIGNALS (derived from object detections; treat as "
        "supporting evidence, not ground truth):\n"
        f"{json.dumps(sport_details, indent=2)}"
        if sport_details
        else ""
    )
    # Tracking-grounded evidence (Phase 10C). Higher-fidelity than the perception
    # summary: player identities, per-frame possession, movement over the whole
    # clip. Only included when detections produced it, so other paths are unchanged.
    tracked_evidence_section = (
        "\n\nTRACKED DETECTION EVIDENCE (object tracking across frames; "
        "higher-fidelity than the perception summary — use it to ground possession, "
        "player identity, and movement direction. track_ids are stable identities, "
        "not roles):\n"
        f"{json.dumps(tracked_evidence, indent=2)}"
        if tracked_evidence
        else ""
    )
    return f"""
Original call: {original_call_line}

PERCEPTION OUTPUT:
{json.dumps(perception, indent=2)}{sport_details_section}{tracked_evidence_section}

SPORT RULEBOOK (the complete rule set for this sport — cite the rule_id that applies):
{_rules_text(rules)}

{_FINAL_JSON_INSTRUCTION}
""".strip()


# Sprint 16B — structured output: the reply is validated against `AdjudicatorResponse`
# and constrained to JSON by the provider, so the model commits directly to the final
# verdict object (the former `<thinking>` scratchpad is incompatible with JSON mode).
# Step-by-step reasoning lives in the schema's `reasoning` field. Shared by both
# adjudicators (the user prompt is built once), so it is sport-agnostic.
_FINAL_JSON_INSTRUCTION = (
    "Output ONLY the final verdict as a single JSON object matching the required schema "
    "— no prose, no markdown fences. The `reasoning` field should be a concise 2-4 "
    "sentence justification that maps the decisive perception facts to the cited rule."
)


def _adjudicator_agent(
    *,
    user_prompt: str,
    framing: str,
    temperature: float,
    sport: str,
) -> dict:
    return _send_validated(
        system_prompt=f"{_get_adjudicator_prompt(sport)}\n\n{framing}",
        user_content=user_prompt,
        temperature=temperature,
        model_cls=AdjudicatorResponse,
        max_tokens=1200,
    )


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
) -> AgentResult:
    # Runs the three real agents: perception, then adjudicators A ∥ B (Sprint 16A
    # removed the retrieval agent — the sport rule corpus is injected in full). The
    # function name and the ``anthropic_four_agent`` provider tag below are kept
    # unchanged as backward-compatible seams (monkeypatch targets, the
    # `_real_pipeline_ran` check, persisted diagnostics).
    #
    # Provider selection is delegated to the factory: an invalid AI_PROVIDER
    # raises a clear error here rather than silently degrading. The mock provider
    # takes the canned demo path; real providers (anthropic, gemini) run the
    # agents through the shared `_send_messages` seam.
    provider = _active_provider()

    if provider.is_mock:
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
        # Sport plugins (Sprint 9): the sport-specific behavior — sport-details
        # extraction and tracking evidence — is owned by the Sport plugin, so the
        # pipeline never checks `sport == "basketball"`. Unknown sports resolve to
        # a GenericSport (no tracking / no game context), preserving prior behavior.
        sport_impl = get_sport(sport)
        # Perception runs through the detector registry (default: claude_vision,
        # which delegates to _perception_agent — behavior is unchanged).
        detector = get_detector()
        detector_result = detector.detect(frame_paths, sport, original_call)
        perception = detector_result.perception
        detections = detector_result.detections
        # Sprint 16A: no retrieval stage. The sport's rule corpus is small enough
        # to inject in full, so both adjudicators see every rule and cite directly.
        # An unregistered sport (GenericSport) yields an empty corpus.
        rules = list(_rule_records(sport))
        # Feed detection-derived sport signals to adjudication only when present,
        # so enriched signals influence verdicts without changing the default path.
        sport_details_for_adjudication = sport_impl.sport_details(detections, perception)
        # Tracking-grounded evidence for adjudication + confidence calibration.
        # The Sport plugin decides whether its sport has a tracking layer.
        tracked_evidence = sport_impl.tracked_evidence(detections)
        # Both adjudicators receive the identical user prompt (only the system
        # framing + temperature differ), so build it once (Sprint 6 perf).
        adjudicator_prompt = _build_adjudicator_prompt(
            perception=perception,
            rules=rules,
            original_call=original_call,
            sport_details=sport_details_for_adjudication,
            tracked_evidence=tracked_evidence,
        )
        # Adjudicators A and B are independent model calls with no shared state:
        # run them concurrently (Sprint 6 perf). The provider does blocking socket
        # I/O, which releases the GIL, so two threads give real wall-clock overlap
        # — cutting adjudication latency from ~2x a model round-trip to ~1x. A
        # failure in either thread re-raises via .result() and is caught by the
        # surrounding except, preserving the exact mock-fallback behavior.
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_a = pool.submit(
                _adjudicator_agent,
                user_prompt=adjudicator_prompt,
                framing=CONSERVATIVE_FRAMING,
                temperature=0.2,
                sport=sport,
            )
            future_b = pool.submit(
                _adjudicator_agent,
                user_prompt=adjudicator_prompt,
                framing=SKEPTICAL_FRAMING,
                temperature=0.7,
                sport=sport,
            )
            adjudicator_a = future_a.result()
            adjudicator_b = future_b.result()
        return {
            "provider_used": "anthropic_four_agent",
            "detector": detector.name,
            "rules": rules,
            "perception": perception,
            "detections": detections,
            "tracked_evidence": tracked_evidence,
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


def _rule_by_id(rule_id: str | None, rules: list[RuleRecord]) -> RuleRecord:
    if rule_id:
        normalized = rule_id.upper()
        for rule in rules:
            if rule["rule_id"].upper() == normalized:
                return rule
    return rules[0] if rules else {
        "rule_id": "NO_RULE",
        "section_title": "No applicable rule found",
        "text": "No specific rules were available for this play.",
        "page_number": 0,
        "call_type": "Unknown",
        "similarity_score": 0.0,
    }


def _reconcile(
    adjudicator_a: dict,
    adjudicator_b: dict,
    perception: dict,
    detection_confidence: float | None = None,
) -> tuple[str, float, str]:
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
        agreed = (confidence_a + confidence_b + perception_confidence) / 3
        # Calibrate with tracking coverage when available: strong tracking nudges
        # up, weak tracking nudges toward caution. Bounded to ±0.05 so detections
        # calibrate but never override the adjudicators. None => unchanged.
        if detection_confidence is not None:
            agreed += 0.1 * (_safe_float(detection_confidence, 0.5) - 0.5)
        # Visual-quality calibration (Sprint 14): shrink toward the 0.5 prior as
        # footage degrades. `clear` is identity, so well-conditioned clips (and the
        # existing reconciliation tests) are unchanged; `partial` footage yields a
        # better-calibrated, less over-confident number.
        agreed = calibrate_confidence(agreed, visual_quality)
        return (
            verdict_a,
            round(max(0.0, min(1.0, agreed)), 2),
            "Both adjudicators reached the same verdict from different review postures, increasing confidence in the final call.",
        )

    return (
        "inconclusive",
        round(min(confidence_a, confidence_b, perception_confidence), 2),
        "The conservative and skeptical adjudicators disagreed, which signals that the clip does not support a confident final verdict.",
    )


def _sport_details_payload(
    sport: str,
    perception: dict,
    detections: RawDetections | None = None,
) -> dict:
    """Build the additive `sport_details` block via the sport detail extractor.

    When `detections` are available the extractor derives sport-specific values
    from them (Phase 6/7); otherwise it reproduces the legacy basketball block
    exactly from the perception payload, preserving backward compatibility.
    Keyed by sport so the frontend reads ``sport_details[sport]``.
    """
    details = get_extractor(sport).extract(detections, perception)
    return {sport: details.model_dump()}


def _frontend_perception(
    perception: dict,
    provider_used: str,
    sport: str,
    detections: RawDetections | None = None,
) -> dict:
    # Compute the legacy basketball blocks once so the legacy top-level fields
    # and the new `sport_details` block stay synchronized (Phase 2 migration).
    offensive_control_status = str(perception.get("offensive_control_status") or "unclear")
    defender_status = perception.get("defender_status") or {
        "primary_or_secondary": "unclear",
        "legal_guarding_position": "unclear",
        "feet_set_before_contact": False,
        "moving_direction": "unclear",
        "inside_restricted_area": False,
    }
    court_geometry = perception.get("court_geometry") or {
        "key_zone": "backcourt_or_unclear",
        "restricted_area_arc_visible": False,
        "defender_feet_visible": False,
        "basket_visible": False,
    }
    return {
        # New additive fields (Phase 2). Legacy fields below are preserved as-is.
        "schema_version": SCHEMA_VERSION,
        "sport": sport,
        "event_type": str(perception.get("event_type") or "unclear"),
        "summary": str(perception.get("summary") or "The perception agent reviewed the submitted basketball play."),
        "players_involved": perception.get("players_involved")
        or [
            {
                "role": "unclear",
                "jersey_color": None,
                "position_description": "Player positions were not clear enough to label.",
                "court_zone": "backcourt_or_unclear",
                "body_state": "Unclear",
            }
        ],
        "contact_detected": bool(perception.get("contact_detected", False)),
        "contact_location": str(perception.get("contact_location") or "unclear"),
        "ball_visible": bool(perception.get("ball_visible", False)),
        "ball_state": str(perception.get("ball_state") or "unclear"),
        "offensive_control_status": offensive_control_status,
        "defender_status": defender_status,
        "court_geometry": court_geometry,
        "frame_observations": perception.get("frame_observations") or [],
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
        "sport_details": _sport_details_payload(sport, perception, detections),
        "notes": (
            f"analysis_provider={provider_used}; "
            f"contact_location={perception.get('contact_location', 'unclear')}; "
            f"ball_state={perception.get('ball_state', 'unclear')}; "
            f"court_geometry={perception.get('court_geometry', {})}; "
            f"defender_status={perception.get('defender_status', {})}; "
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
    agent_result: AgentResult,
    clip_id: str,
    frame_paths: list[Path],
    video_metadata: dict | None,
    processing_time_seconds: float,
    sport: str,
) -> dict:
    perception = agent_result["perception"]
    detections = agent_result.get("detections")
    rules = agent_result["rules"]
    provider_used = agent_result["provider_used"]
    adjudicator_a_raw = agent_result["adjudicator_a"]
    adjudicator_b_raw = agent_result["adjudicator_b"]
    tracked_evidence = agent_result.get("tracked_evidence")
    detection_confidence = (
        tracked_evidence.get("tracking_confidence") if isinstance(tracked_evidence, dict) else None
    )
    final_verdict, final_confidence, reconciliation_note = _reconcile(
        adjudicator_a_raw, adjudicator_b_raw, perception, detection_confidence
    )
    primary_rule = _rule_by_id(
        adjudicator_a_raw.get("primary_rule_id") or adjudicator_b_raw.get("primary_rule_id"),
        rules,
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
            "perception": _frontend_perception(perception, provider_used, sport, detections),
            "adjudicator_a": adjudicator_a,
            "adjudicator_b": adjudicator_b,
            "reconciliation_note": reconciliation_note,
            "processing_time_seconds": round(processing_time_seconds, 1),
        },
        "diagnostics": _diagnostics_payload(
            provider_used,
            detections,
            detector=agent_result.get("detector"),
            frames_analyzed=len(frame_paths),
            fallback_reason=agent_result.get("fallback_reason"),
            tracked_evidence=tracked_evidence,
        ),
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
    from rules.sport_config import normalize_sport

    start = perf_counter()
    normalized_sport = normalize_sport(sport)
    normalized_level = _clean(level_of_play)
    normalized_league = _clean(league)
    normalized_original_call = _clean(original_call)
    normalized_referee_name = _clean(referee_name)
    clip_id = _clip_id(video_metadata)

    # Opt-in result cache: return a prior identical analysis without any model
    # calls. Default OFF (see _analysis_cache_enabled) so behavior is unchanged.
    cache_enabled = _analysis_cache_enabled()
    cache_key = (
        _analysis_cache_key(
            clip_id,
            normalized_sport,
            normalized_level,
            normalized_league,
            normalized_original_call,
            normalized_referee_name,
        )
        if cache_enabled
        else ""
    )
    if cache_enabled:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

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

    response = _build_response(
        agent_result=agent_result,
        clip_id=clip_id,
        frame_paths=frame_paths,
        video_metadata=video_metadata,
        processing_time_seconds=perf_counter() - start,
        sport=normalized_sport,
    )

    # Additive, basketball-only game-context enrichment. Fully guarded: any
    # failure (missing nba_api, network, bad data) is swallowed so the verdict
    # is never affected. Non-basketball sports get no game_context field.
    metadata_attempted = False
    metadata_status = "not_applicable"
    try:
        from services.metadata import resolve_clip_game_context

        game_context = resolve_clip_game_context(
            sport=normalized_sport,
            league=normalized_league,
            original_call=normalized_original_call,
            video_metadata=video_metadata,
        )
        if game_context is not None:
            metadata_attempted = True
            payload = game_context.model_dump()
            response["game_context"] = payload
            metadata_status = payload.get("resolution_status", "unresolved")
    except Exception:
        metadata_attempted = True
        metadata_status = "unavailable"

    # Surface metadata status in diagnostics (additive; never affects the verdict).
    diagnostics = response.get("diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics["metadata_attempted"] = metadata_attempted
        diagnostics["metadata_status"] = metadata_status

    if cache_enabled:
        _cache_put(cache_key, response)

    return response
