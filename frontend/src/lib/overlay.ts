// AI reasoning overlay helpers (Sprint 4).
//
// Pure, framework-free logic so the overlay geometry and timelines are
// unit-testable in isolation (mirrors the sportEvidence.ts pattern). React
// components in src/app/components/ consume these.
//
// Positional data: the backend exposes the AI's semantic perception, an impact
// zone (real, normalized coordinates), and tracking *diagnostics* (counts,
// possession summary, movement direction, tracking confidence) — but not raw
// per-frame CV bounding boxes. So player/ball markers are placed by an
// AI-reasoning layout anchored on the impact zone and driven by the detected
// roles/possession/movement. Everything here is derived from real response data.

import type { EventDescription } from "./types";
import { overlayVocab } from "./sports";

export type MarkerKind = "offense" | "defense" | "ball";

export interface OverlayMarker {
  id: string;
  kind: MarkerKind;
  /** Position as a percentage of the frame (0-100). */
  x: number;
  y: number;
  label: string;
  sublabel: string;
  /** Primary offensive player / primary defender / the ball. */
  primary: boolean;
  /** Coarse movement vector in image space, or null when stationary/unknown. */
  movement: MovementVector | null;
}

export interface MovementVector {
  dx: number;
  dy: number;
  /** Angle in degrees for rotating an arrow glyph (0 = pointing right). */
  angleDeg: number;
  label: string;
}

export interface ImpactZone {
  x_percent: number;
  y_percent: number;
  radius_percent: number;
  label: string;
}

export interface TimelineEvent {
  id: string;
  seconds: number;
  label: string;
  kind: "observation" | "moment" | "key";
}

export interface KeyFrame {
  id: string;
  seconds: number;
  label: string;
  frameIndex: number | null;
}

export interface PossessionSegment {
  label: string;
  /** Start/end as a fraction (0-1) of the timeline. */
  start: number;
  end: number;
}

const clamp = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

const humanize = (value: string | null | undefined): string =>
  value ? value.replace(/_/g, " ") : "unclear";

/**
 * Map a coarse image-space direction word (from a sport's directional signals) to
 * an arrow vector. Labels are sport-neutral. Returns null when the subject is
 * stationary or the direction is unknown, so callers draw no arrow.
 */
export function movementVector(direction: string | null | undefined): MovementVector | null {
  switch ((direction || "").toLowerCase().trim()) {
    case "lateral":
      return { dx: 1, dy: 0, angleDeg: 0, label: "moving laterally" };
    case "vertical": // upward in image space
      return { dx: 0, dy: -1, angleDeg: -90, label: "moving up" };
    case "forward": // downward in image space (toward camera / attacking end)
      return { dx: 0, dy: 1, angleDeg: 90, label: "moving forward" };
    case "driving":
    case "dribbling":
    case "carrying":
      return { dx: -1, dy: 1, angleDeg: 135, label: "driving with the ball" };
    default:
      return null;
  }
}

interface DirectionalHints {
  offensiveControl?: string;
  defenderDirection?: string;
}

/**
 * Read the directional signals for the sport, if the sport's detail block exposes
 * them (basketball's defender_status / offensive_control_status). Falls back to
 * the legacy top-level fields. Sports without directional data yield no hints, so
 * no movement arrows are drawn — a graceful, sport-agnostic default.
 */
function directionalHints(perception: EventDescription, sportKey: string): DirectionalHints {
  const block = perception.sport_details?.[sportKey] as
    | { offensive_control_status?: string; defender_status?: { moving_direction?: string } }
    | undefined;
  return {
    offensiveControl: block?.offensive_control_status ?? perception.offensive_control_status,
    defenderDirection:
      block?.defender_status?.moving_direction ?? perception.defender_status?.moving_direction,
  };
}

interface PlacementSpec {
  dx: number; // offset from impact zone, in frame-percent
  dy: number;
}

// Reasoning layout: offense attacks from below-left of the point of contact, the
// primary defender contests from above-right, extra players fan outward.
const OFFENSE_ANCHOR: PlacementSpec = { dx: -13, dy: 9 };
const DEFENSE_ANCHOR: PlacementSpec = { dx: 13, dy: -7 };
const FAN_STEP = 11;

/**
 * Build player + ball markers positioned around the impact zone from the AI's
 * perception. Sport-aware: marker labels come from the sport's overlay vocabulary
 * (`sports.ts`), so the layout reads correctly for basketball, soccer, hockey,
 * lacrosse, or any future sport (neutral default). Deterministic so the same
 * analysis always renders the same layout.
 */
export function buildOverlayMarkers(
  perception: EventDescription,
  impact: ImpactZone,
  sport: string = perception.sport,
): OverlayMarker[] {
  const cx = clamp(impact.x_percent, 6, 94);
  const cy = clamp(impact.y_percent, 6, 94);
  const markers: OverlayMarker[] = [];

  const sportKey = (sport || "").toLowerCase().trim();
  const vocab = overlayVocab(sportKey);
  const players = perception.players_involved ?? [];
  const { offensiveControl, defenderDirection } = directionalHints(perception, sportKey);

  let offenseSeen = 0;
  let defenseSeen = 0;
  players.forEach((player, index) => {
    const isDefense = player.role === "defense";
    const anchor = isDefense ? DEFENSE_ANCHOR : OFFENSE_ANCHOR;
    const rank = isDefense ? defenseSeen : offenseSeen;
    const sign = isDefense ? 1 : -1;
    const x = clamp(cx + anchor.dx + sign * rank * FAN_STEP, 4, 96);
    const y = clamp(cy + anchor.dy + rank * 4, 4, 96);
    const primary = rank === 0;
    const movement = isDefense
      ? movementVector(defenderDirection)
      : movementVector(offensiveControl);
    markers.push({
      id: `player-${index}`,
      kind: isDefense ? "defense" : "offense",
      x,
      y,
      label: isDefense
        ? primary
          ? vocab.defense
          : vocab.defenseSecondary
        : primary
          ? vocab.offense
          : vocab.offenseSecondary,
      sublabel: [player.jersey_color, humanize(player.body_state)]
        .filter(Boolean)
        .join(" · "),
      primary,
      movement,
    });
    if (isDefense) defenseSeen += 1;
    else offenseSeen += 1;
  });

  if (perception.ball_visible) {
    markers.push({
      id: "ball",
      kind: "ball",
      x: cx,
      y: cy,
      label: vocab.object,
      sublabel: humanize(perception.ball_state),
      primary: true,
      movement: movementVector(offensiveControl),
    });
  }

  return markers;
}

/** True when the perception actually located at least one offense/defense role. */
export function hasTrackedPlayers(perception: EventDescription): boolean {
  return (perception.players_involved ?? []).some(
    (p) => p.role === "offense" || p.role === "defense",
  );
}

/**
 * Ordered timeline of AI-observed events: per-frame observations, the moment of
 * the call, and the key moment. Deduplicated-ish and sorted by time.
 */
export function buildEventTimeline(
  perception: EventDescription,
  keyMomentSeconds: number | null | undefined,
): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  (perception.frame_observations ?? []).forEach((obs, index) => {
    events.push({
      id: `obs-${index}`,
      seconds: Math.max(0, Number(obs.approx_time_seconds) || 0),
      label: obs.observation || `Frame ${obs.frame_index}`,
      kind: "observation",
    });
  });
  if (perception.moment_of_interest_seconds != null) {
    events.push({
      id: "moment",
      seconds: Math.max(0, perception.moment_of_interest_seconds),
      label: "Moment of the call",
      kind: "moment",
    });
  }
  if (keyMomentSeconds != null) {
    events.push({
      id: "key",
      seconds: Math.max(0, keyMomentSeconds),
      label: "Key frame",
      kind: "key",
    });
  }
  return events.sort((a, b) => a.seconds - b.seconds);
}

/** Navigable key frames: each per-frame observation plus the key moment. */
export function buildKeyFrames(
  perception: EventDescription,
  keyMoment: { frame_number?: number; approximate_seconds?: number | null } | null | undefined,
): KeyFrame[] {
  const frames: KeyFrame[] = (perception.frame_observations ?? []).map((obs, index) => ({
    id: `frame-${index}`,
    seconds: Math.max(0, Number(obs.approx_time_seconds) || 0),
    label: obs.observation ? obs.observation.slice(0, 42) : `Frame ${obs.frame_index}`,
    frameIndex: obs.frame_index,
  }));
  if (keyMoment?.approximate_seconds != null) {
    frames.push({
      id: "keyframe",
      seconds: Math.max(0, keyMoment.approximate_seconds),
      label: "Key moment",
      frameIndex: keyMoment.frame_number ?? null,
    });
  }
  return frames.sort((a, b) => a.seconds - b.seconds);
}

/**
 * Possession segments across the clip. The backend gives a possession *summary*
 * (dribbling / passing / gathered / loose_ball), not a per-frame timeline, so we
 * render one segment — or two for "passing" (a handoff) — labeled from the AI's
 * possession read.
 */
export function possessionSegments(
  possessionSummary: string | null | undefined,
  offensiveControl: string | null | undefined,
): PossessionSegment[] {
  const summary = (possessionSummary || offensiveControl || "").toLowerCase().trim();
  if (summary === "passing") {
    return [
      { label: "Passer", start: 0, end: 0.5 },
      { label: "Receiver", start: 0.5, end: 1 },
    ];
  }
  if (!summary || summary === "unclear") {
    return [{ label: "possession unclear", start: 0, end: 1 }];
  }
  return [{ label: humanize(summary), start: 0, end: 1 }];
}
