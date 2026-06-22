"""Sport-agnostic perception schema (foundation).

Phase 0 + Phase 1 of docs/superpowers/plans/2026-06-12-sport-agnostic-perception.md.

This module is INTENTIONALLY standalone: nothing in the runtime pipeline imports
it yet. It formalizes the perception contract as Pydantic v2 models so later
phases can migrate `ai_analyzer.py` onto it without changing behavior now.

- Phase 0: the sport-neutral common core (`PerceptionCore` and its parts).
- Phase 1: the per-sport `SportDetails` extension models + registry.

`PerceptionCore` deliberately does NOT embed `sport_details` yet — composing the
two is a Phase 2 wiring concern. `RawDetections`/`detections` (YOLO) is deferred
to Phase 5.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Bump on any breaking change to the perception contract. Gates cache + validation
# once the runtime is migrated onto this schema (Phase 2+).
SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Shared value vocabularies (sport-neutral)
# ---------------------------------------------------------------------------

VisualQuality = Literal["clear", "partial", "obstructed", "poor"]
PlayerRole = Literal["offense", "defense", "unclear"]
ContactSeverity = Literal["incidental", "significant", "unclear", "none"]
ObjectKind = Literal["ball", "puck"]


# ---------------------------------------------------------------------------
# Phase 0 — common core component models
# ---------------------------------------------------------------------------

class FrameObservation(BaseModel):
    """A single concrete observation tied to one extracted frame."""

    frame_index: int
    approx_time_seconds: float = 0.0
    observation: str = ""


class Player(BaseModel):
    """A player involved in the key moment.

    `zone` is a generic string whose vocabulary is sport-defined (basketball:
    "paint_lane"; hockey: "offensive_zone"; soccer: "attacking_third"), so the
    core stays neutral while preserving per-sport meaning.
    """

    role: PlayerRole = "unclear"
    team_color: str | None = None
    position_description: str = ""
    body_state: str = ""
    zone: str | None = None


class Contact(BaseModel):
    """Generalizes the legacy `contact_detected` / `contact_location` fields."""

    detected: bool = False
    location: str = "unclear"
    severity: ContactSeverity = "unclear"


class ObjectOfPlay(BaseModel):
    """Generalizes the legacy `ball_visible` / `ball_state` fields.

    `kind` distinguishes a ball (basketball/soccer/lacrosse) from a puck
    (hockey). `state` vocabulary is sport-defined.
    """

    kind: ObjectKind = "ball"
    visible: bool = False
    state: str = "unclear"


class ImpactZone(BaseModel):
    """Normalized (0..100) frame region marking the decisive point of action."""

    x_percent: float = 50.0
    y_percent: float = 50.0
    radius_percent: float = 14.0
    label: str = ""


class PerceptionCore(BaseModel):
    """Sport-neutral perception payload shared by every sport.

    Sport-specific observations live in a separate `SportDetails` model
    (Phase 1) and are composed in during the Phase 2 rewire — not here.
    """

    schema_version: int = SCHEMA_VERSION
    sport: str
    event_type: str = "unclear"
    summary: str = ""
    players_involved: list[Player] = Field(default_factory=list)
    contact: Contact = Field(default_factory=Contact)
    object_of_play: ObjectOfPlay = Field(default_factory=ObjectOfPlay)
    frame_observations: list[FrameObservation] = Field(default_factory=list)
    moment_of_interest_seconds: float | None = None
    impact_zone: ImpactZone = Field(default_factory=ImpactZone)
    visual_quality: VisualQuality = "partial"
    perception_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: str | None = None


# ---------------------------------------------------------------------------
# Phase 1 — per-sport detail extension models + registry
#
# `SportDetails` subclasses hold the sport-specific observations that do NOT
# belong in the neutral core. They are standalone here; composing them into the
# response is a Phase 2 concern. BasketballDetails is a LOSSLESS move of the
# fields `_frontend_perception()` emits today.
# ---------------------------------------------------------------------------

class SportDetails(BaseModel):
    """Base class for every sport's perception extension block."""


class EmptySportDetails(SportDetails):
    """Fallback for sports with no configured detail schema yet."""


class DefenderStatus(BaseModel):
    """Basketball defender legality block (verbatim from current output)."""

    primary_or_secondary: str = "unclear"
    legal_guarding_position: str = "unclear"
    feet_set_before_contact: bool = False
    moving_direction: str = "unclear"
    inside_restricted_area: bool = False


class CourtGeometry(BaseModel):
    """Basketball court-geometry block (verbatim from current output)."""

    key_zone: str = "backcourt_or_unclear"
    restricted_area_arc_visible: bool = False
    defender_feet_visible: bool = False
    basket_visible: bool = False


class BasketballDetails(SportDetails):
    """Basketball-specific perception fields, preserved exactly as produced today."""

    offensive_control_status: str = "unclear"
    defender_status: DefenderStatus = Field(default_factory=DefenderStatus)
    court_geometry: CourtGeometry = Field(default_factory=CourtGeometry)


class HockeyDetails(SportDetails):
    """Minimal hockey placeholder (no rules/perception authored yet)."""

    zone: str = "unclear"
    goalie_involved: bool = False
    puck_possession: str = "unclear"
    infraction_candidate: str = "unclear"
    boards_involved: bool = False


class SoccerDetails(SportDetails):
    """Minimal soccer placeholder (no rules/perception authored yet)."""

    field_third: str = "unclear"
    in_penalty_area: bool = False
    offside_relevant: bool = False
    last_defender: bool = False
    handball_candidate: bool = False
    foul_direction: str = "unclear"


class LacrosseDetails(SportDetails):
    """Minimal lacrosse placeholder (no rules/perception authored yet)."""

    crease_violation: bool = False
    cross_check: bool = False
    slashing: bool = False
    ball_carrier_status: str = "unclear"
    warding: bool = False


# Keys must match keys in rules.sport_config.SPORTS. Mirrors the
# `_PERCEPTION_PROMPTS` selector pattern in ai_analyzer.py.
SPORT_DETAIL_MODELS: dict[str, type[SportDetails]] = {
    "basketball": BasketballDetails,
    "hockey": HockeyDetails,
    "soccer": SoccerDetails,
    "lacrosse": LacrosseDetails,
}


def get_sport_details_model(sport: str) -> type[SportDetails]:
    """Return the SportDetails subclass for a sport.

    Case-insensitive. Unknown/unconfigured sports fall back to
    `EmptySportDetails` (never raises), matching `_get_perception_prompt`'s
    stub-fallback behavior. Callers normalize sport upstream via
    `rules.sport_config.normalize_sport`.
    """
    normalized = sport.lower().strip() if sport else ""
    return SPORT_DETAIL_MODELS.get(normalized, EmptySportDetails)
