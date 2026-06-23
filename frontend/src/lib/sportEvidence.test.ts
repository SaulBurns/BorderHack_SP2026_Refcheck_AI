import { describe, expect, it } from "vitest";

import { sportEvidenceRows, sportLabel } from "./sportEvidence";
import type { EventDescription, SportDetailsMap } from "./types";

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

const basketballDetails = (
  keyZone: string,
  legalGuardingPosition: string,
): SportDetailsMap => ({
  basketball: {
    offensive_control_status: "airborne_shooter",
    defender_status: {
      primary_or_secondary: "secondary",
      legal_guarding_position: legalGuardingPosition,
      feet_set_before_contact: false,
      moving_direction: "lateral",
      inside_restricted_area: true,
    },
    court_geometry: {
      key_zone: keyZone,
      restricted_area_arc_visible: true,
      defender_feet_visible: true,
      basket_visible: true,
    },
  },
});


describe("basketball evidence (parity with pre-migration rendering)", () => {
  it("always returns exactly two rows", () => {
    const rows = sportEvidenceRows("basketball", makePerception());
    expect(rows).toHaveLength(2);
    expect(rows.map((r) => r.label)).toEqual(["Court zone known", "Defender status"]);
  });

  it("reads from sport_details when present (known zone + established defender)", () => {
    const p = makePerception({ sport_details: basketballDetails("restricted_area", "established") });
    const rows = sportEvidenceRows("basketball", p);
    expect(rows[0]).toEqual({ label: "Court zone known", value: true, detail: "restricted area" });
    expect(rows[1]).toEqual({ label: "Defender status", value: true, detail: "established" });
  });

  it("renders unclear/backcourt as not-satisfied", () => {
    const p = makePerception({ sport_details: basketballDetails("backcourt_or_unclear", "unclear") });
    const rows = sportEvidenceRows("basketball", p);
    expect(rows[0]).toEqual({ label: "Court zone known", value: false, detail: "backcourt or unclear" });
    expect(rows[1]).toEqual({ label: "Defender status", value: false, detail: "unclear" });
  });

  it("falls back to legacy top-level fields when sport_details is absent", () => {
    const p = makePerception({
      court_geometry: {
        key_zone: "restricted_area",
        restricted_area_arc_visible: true,
        defender_feet_visible: true,
        basket_visible: true,
      },
      defender_status: {
        primary_or_secondary: "secondary",
        legal_guarding_position: "established",
        feet_set_before_contact: true,
        moving_direction: "vertical",
        inside_restricted_area: true,
      },
    });
    const rows = sportEvidenceRows("basketball", p);
    expect(rows[0].value).toBe(true);
    expect(rows[0].detail).toBe("restricted area");
    expect(rows[1].value).toBe(true);
    expect(rows[1].detail).toBe("established");
  });

  it("prefers sport_details over legacy fields when both present", () => {
    const p = makePerception({
      sport_details: basketballDetails("restricted_area", "established"),
      court_geometry: {
        key_zone: "backcourt_or_unclear",
        restricted_area_arc_visible: false,
        defender_feet_visible: false,
        basket_visible: false,
      },
    });
    const rows = sportEvidenceRows("basketball", p);
    expect(rows[0].detail).toBe("restricted area");
    expect(rows[0].value).toBe(true);
  });

  it("is case-insensitive on the sport id", () => {
    expect(sportEvidenceRows("Basketball", makePerception())).toHaveLength(2);
  });
});


describe("placeholder sports render gracefully", () => {
  it("hockey returns rows even with empty sport_details", () => {
    const rows = sportEvidenceRows("hockey", makePerception({ sport: "hockey" }));
    expect(rows.map((r) => r.label)).toEqual(["Zone identified", "Goalie involved"]);
    expect(rows[0]).toEqual({ label: "Zone identified", value: false, detail: "unclear" });
    expect(rows[1]).toEqual({ label: "Goalie involved", value: false, detail: "no" });
  });

  it("hockey reflects populated sport_details", () => {
    const p = makePerception({
      sport: "hockey",
      sport_details: {
        hockey: {
          zone: "offensive_zone",
          goalie_involved: true,
          puck_possession: "unclear",
          infraction_candidate: "boarding",
          boards_involved: true,
        },
      },
    });
    const rows = sportEvidenceRows("hockey", p);
    expect(rows[0]).toEqual({ label: "Zone identified", value: true, detail: "offensive zone" });
    expect(rows[1]).toEqual({ label: "Goalie involved", value: true, detail: "yes" });
  });

  it("soccer returns graceful placeholder rows", () => {
    const rows = sportEvidenceRows("soccer", makePerception({ sport: "soccer" }));
    expect(rows.map((r) => r.label)).toEqual(["Field third known", "In penalty area"]);
    expect(rows.every((r) => r.value === false)).toBe(true);
  });

  it("lacrosse returns graceful placeholder rows", () => {
    const rows = sportEvidenceRows("lacrosse", makePerception({ sport: "lacrosse" }));
    expect(rows.map((r) => r.label)).toEqual(["Ball carrier status", "Crease violation"]);
    expect(rows.every((r) => r.value === false)).toBe(true);
  });
});


describe("unknown sports degrade gracefully", () => {
  it("returns no sport-specific rows", () => {
    expect(sportEvidenceRows("curling", makePerception({ sport: "curling" }))).toEqual([]);
    expect(sportEvidenceRows("", makePerception())).toEqual([]);
  });
});


describe("sportLabel", () => {
  it("capitalizes the sport id", () => {
    expect(sportLabel("basketball")).toBe("Basketball");
    expect(sportLabel("hockey")).toBe("Hockey");
    expect(sportLabel("soccer")).toBe("Soccer");
    expect(sportLabel("lacrosse")).toBe("Lacrosse");
  });

  it("handles empty input", () => {
    expect(sportLabel("")).toBe("Unknown");
  });
});
