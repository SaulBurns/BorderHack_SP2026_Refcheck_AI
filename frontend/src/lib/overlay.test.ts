import { describe, expect, it } from "vitest";

import {
  buildEventTimeline,
  buildKeyFrames,
  buildOverlayMarkers,
  hasTrackedPlayers,
  movementVector,
  possessionSegments,
  type ImpactZone,
} from "./overlay";
import type { EventDescription } from "./types";

function makePerception(overrides: Partial<EventDescription> = {}): EventDescription {
  return {
    schema_version: 1,
    sport: "basketball",
    event_type: "unclear",
    summary: "a play",
    players_involved: [],
    contact_detected: false,
    contact_location: "unclear",
    ball_visible: false,
    ball_state: "unclear",
    moment_of_interest_seconds: null,
    visual_quality: "partial",
    perception_confidence: 0.5,
    notes: null,
    ...overrides,
  };
}

const IMPACT: ImpactZone = {
  x_percent: 50,
  y_percent: 50,
  radius_percent: 14,
  label: "impact",
};

// ---------------------------------------------------------------------------
// movementVector
// ---------------------------------------------------------------------------

describe("movementVector", () => {
  it("maps known directions to arrow vectors", () => {
    expect(movementVector("lateral")?.angleDeg).toBe(0);
    expect(movementVector("vertical")?.angleDeg).toBe(-90);
    expect(movementVector("forward")?.angleDeg).toBe(90);
    // Labels are sport-neutral (no basketball vocabulary).
    expect(movementVector("driving")?.label).toContain("driving");
  });

  it("returns null for stationary/unknown", () => {
    expect(movementVector("stationary")).toBeNull();
    expect(movementVector("unclear")).toBeNull();
    expect(movementVector(undefined)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// buildOverlayMarkers
// ---------------------------------------------------------------------------

describe("buildOverlayMarkers", () => {
  it("places offense, defender, and ball markers around the impact zone", () => {
    const perception = makePerception({
      ball_visible: true,
      ball_state: "held",
      players_involved: [
        { role: "offense", jersey_color: "white", position_description: "wing", body_state: "driving" },
        { role: "defense", jersey_color: "blue", position_description: "paint", body_state: "sliding" },
      ],
      sport_details: {
        basketball: {
          offensive_control_status: "driving",
          defender_status: {
            primary_or_secondary: "primary",
            legal_guarding_position: "established",
            feet_set_before_contact: true,
            moving_direction: "lateral",
            inside_restricted_area: false,
          },
          court_geometry: {
            key_zone: "paint_lane",
            restricted_area_arc_visible: true,
            defender_feet_visible: true,
            basket_visible: true,
          },
        },
      },
    });
    const markers = buildOverlayMarkers(perception, IMPACT);
    const kinds = markers.map((m) => m.kind).sort();
    expect(kinds).toEqual(["ball", "defense", "offense"]);
    // primary offense gets the "Ball handler" label, primary defense "Defender".
    expect(markers.find((m) => m.kind === "offense")?.label).toBe("Ball handler");
    expect(markers.find((m) => m.kind === "defense")?.label).toBe("Defender");
    // defender movement uses moving_direction; offense uses offensive_control.
    expect(markers.find((m) => m.kind === "defense")?.movement?.angleDeg).toBe(0); // lateral
    expect(markers.find((m) => m.kind === "offense")?.movement?.label).toContain("driving");
  });

  it("uses sport-aware marker labels", () => {
    const players = [
      { role: "offense" as const, jersey_color: "red", position_description: "x", body_state: "y" },
      { role: "defense" as const, jersey_color: "blue", position_description: "x", body_state: "y" },
    ];
    const soccer = buildOverlayMarkers(
      makePerception({ sport: "soccer", ball_visible: true, players_involved: players }),
      IMPACT,
      "soccer",
    );
    expect(soccer.find((m) => m.kind === "offense")?.label).toBe("Attacker");
    expect(soccer.find((m) => m.kind === "ball")?.label).toBe("Ball");

    const hockey = buildOverlayMarkers(
      makePerception({ sport: "hockey", ball_visible: true, players_involved: players }),
      IMPACT,
      "hockey",
    );
    expect(hockey.find((m) => m.kind === "offense")?.label).toBe("Puck carrier");
    expect(hockey.find((m) => m.kind === "ball")?.label).toBe("Puck");

    // Defaults to the perception's sport when no explicit sport is passed.
    const lacrosse = buildOverlayMarkers(
      makePerception({ sport: "lacrosse", players_involved: players }),
      IMPACT,
    );
    expect(lacrosse.find((m) => m.kind === "offense")?.label).toBe("Ball carrier");
  });

  it("omits the ball marker when the ball is not visible", () => {
    const markers = buildOverlayMarkers(makePerception({ ball_visible: false }), IMPACT);
    expect(markers.some((m) => m.kind === "ball")).toBe(false);
  });

  it("keeps all markers within the frame bounds", () => {
    const perception = makePerception({
      players_involved: Array.from({ length: 4 }, () => ({
        role: "offense" as const,
        jersey_color: "white",
        position_description: "x",
        body_state: "y",
      })),
    });
    const markers = buildOverlayMarkers(perception, { ...IMPACT, x_percent: 2, y_percent: 98 });
    for (const marker of markers) {
      expect(marker.x).toBeGreaterThanOrEqual(0);
      expect(marker.x).toBeLessThanOrEqual(100);
      expect(marker.y).toBeGreaterThanOrEqual(0);
      expect(marker.y).toBeLessThanOrEqual(100);
    }
  });
});

describe("hasTrackedPlayers", () => {
  it("is true only when an offense/defense role is present", () => {
    expect(hasTrackedPlayers(makePerception())).toBe(false);
    expect(
      hasTrackedPlayers(
        makePerception({
          players_involved: [
            { role: "unclear", jersey_color: null, position_description: "", body_state: "" },
          ],
        }),
      ),
    ).toBe(false);
    expect(
      hasTrackedPlayers(
        makePerception({
          players_involved: [
            { role: "defense", jersey_color: null, position_description: "", body_state: "" },
          ],
        }),
      ),
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// timelines
// ---------------------------------------------------------------------------

describe("buildEventTimeline", () => {
  it("merges frame observations, the moment, and the key frame, sorted by time", () => {
    const perception = makePerception({
      moment_of_interest_seconds: 2.0,
      frame_observations: [
        { frame_index: 0, approx_time_seconds: 3.0, observation: "later" },
        { frame_index: 1, approx_time_seconds: 0.5, observation: "early" },
      ],
    });
    const events = buildEventTimeline(perception, 1.0);
    expect(events.map((e) => e.seconds)).toEqual([0.5, 1.0, 2.0, 3.0]);
    expect(events.find((e) => e.kind === "moment")?.seconds).toBe(2.0);
    expect(events.find((e) => e.kind === "key")?.seconds).toBe(1.0);
  });

  it("is empty when there is nothing to show", () => {
    expect(buildEventTimeline(makePerception(), null)).toEqual([]);
  });
});

describe("buildKeyFrames", () => {
  it("includes each observation plus the key moment, sorted", () => {
    const perception = makePerception({
      frame_observations: [{ frame_index: 5, approx_time_seconds: 2.5, observation: "contact" }],
    });
    const frames = buildKeyFrames(perception, {
      frame_number: 9,
      approximate_seconds: 1.0,
    });
    expect(frames.map((f) => f.seconds)).toEqual([1.0, 2.5]);
    expect(frames[0].frameIndex).toBe(9);
    expect(frames[1].frameIndex).toBe(5);
  });
});

describe("possessionSegments", () => {
  it("splits passing into passer/receiver", () => {
    const segments = possessionSegments("passing", null);
    expect(segments.map((s) => s.label)).toEqual(["Passer", "Receiver"]);
    expect(segments[1].end).toBe(1);
  });

  it("returns one labeled segment for dribbling", () => {
    const segments = possessionSegments("dribbling", null);
    expect(segments).toHaveLength(1);
    expect(segments[0].label).toBe("dribbling");
  });

  it("falls back to offensive control then to unclear", () => {
    expect(possessionSegments(null, "gathered")[0].label).toBe("gathered");
    expect(possessionSegments(null, null)[0].label).toBe("possession unclear");
  });
});
