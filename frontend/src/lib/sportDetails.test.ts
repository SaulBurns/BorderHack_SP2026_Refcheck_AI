import { describe, expect, it } from "vitest";

import { dynamicSportDetailRows, diagnosticRows, humanizeKey } from "./sportDetails";
import type { Diagnostics, EventDescription } from "./types";

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

describe("humanizeKey", () => {
  it("turns a snake_case key into a capitalized label", () => {
    expect(humanizeKey("field_third")).toBe("Field third");
    expect(humanizeKey("in_penalty_area")).toBe("In penalty area");
  });
});

describe("dynamicSportDetailRows", () => {
  it("returns [] when there is no sport_details block for the sport", () => {
    expect(dynamicSportDetailRows("soccer", makePerception({ sport: "soccer" }))).toEqual([]);
  });

  it("renders a flat sport_details block field-by-field (soccer)", () => {
    const p = makePerception({
      sport: "soccer",
      sport_details: {
        soccer: {
          field_third: "attacking_third",
          in_penalty_area: true,
          offside_relevant: false,
          last_defender: false,
          handball_candidate: true,
          foul_direction: "defender_on_attacker",
        },
      },
    });
    const rows = dynamicSportDetailRows("soccer", p);
    expect(rows).toEqual([
      { label: "Field third", value: true, detail: "attacking third" },
      { label: "In penalty area", value: true, detail: "yes" },
      { label: "Offside relevant", value: false, detail: "no" },
      { label: "Last defender", value: false, detail: "no" },
      { label: "Handball candidate", value: true, detail: "yes" },
      { label: "Foul direction", value: true, detail: "defender on attacker" },
    ]);
  });

  it("treats 'unclear' string values as not-satisfied", () => {
    const p = makePerception({
      sport: "hockey",
      sport_details: { hockey: { zone: "unclear", goalie_involved: false } },
    });
    const rows = dynamicSportDetailRows("hockey", p);
    expect(rows[0]).toEqual({ label: "Zone", value: false, detail: "unclear" });
  });

  it("flattens nested objects (basketball defender_status / court_geometry)", () => {
    const p = makePerception({
      sport: "basketball",
      sport_details: {
        basketball: {
          offensive_control_status: "airborne_shooter",
          defender_status: {
            primary_or_secondary: "secondary",
            legal_guarding_position: "established",
            feet_set_before_contact: true,
            moving_direction: "lateral",
            inside_restricted_area: true,
          },
          court_geometry: {
            key_zone: "restricted_area",
            restricted_area_arc_visible: true,
            defender_feet_visible: true,
            basket_visible: true,
          },
        },
      },
    });
    const rows = dynamicSportDetailRows("basketball", p);
    const byLabel = Object.fromEntries(rows.map((r) => [r.label, r]));
    expect(byLabel["Offensive control status"]).toEqual({
      label: "Offensive control status",
      value: true,
      detail: "airborne shooter",
    });
    // Nested leaf keys are flattened in.
    expect(byLabel["Legal guarding position"].detail).toBe("established");
    expect(byLabel["Key zone"].detail).toBe("restricted area");
    expect(byLabel["Inside restricted area"]).toEqual({
      label: "Inside restricted area",
      value: true,
      detail: "yes",
    });
  });

  it("works for a sport the frontend does not know statically", () => {
    const p = makePerception({
      sport: "underwater_hockey",
      sport_details: { underwater_hockey: { surfaced: true, depth_zone: "deep" } },
    });
    const rows = dynamicSportDetailRows("underwater_hockey", p);
    expect(rows).toEqual([
      { label: "Surfaced", value: true, detail: "yes" },
      { label: "Depth zone", value: true, detail: "deep" },
    ]);
  });

  it("is case-insensitive on the sport id", () => {
    const p = makePerception({
      sport: "Soccer",
      sport_details: { soccer: { in_penalty_area: true } },
    });
    expect(dynamicSportDetailRows("Soccer", p)).toEqual([
      { label: "In penalty area", value: true, detail: "yes" },
    ]);
  });
});

describe("diagnosticRows", () => {
  it("returns [] for missing diagnostics", () => {
    expect(diagnosticRows(undefined)).toEqual([]);
  });

  it("renders present diagnostic fields generically", () => {
    const diagnostics: Diagnostics = {
      detector: "hybrid",
      provider_used: "anthropic_four_agent",
      tracked_evidence_present: true,
      tracking_confidence: 0.42,
      possession_summary: "in_possession",
      yolo_influenced: true,
      player_count: 3,
    };
    const rows = diagnosticRows(diagnostics);
    const byLabel = Object.fromEntries(rows.map((r) => [r.label, r]));
    expect(byLabel["Detector"].detail).toBe("hybrid");
    expect(byLabel["Tracked evidence present"]).toEqual({
      label: "Tracked evidence present",
      value: true,
      detail: "yes",
    });
    expect(byLabel["Tracking confidence"].detail).toBe("42%");
    expect(byLabel["Possession summary"].detail).toBe("in possession");
    expect(byLabel["Players tracked"].detail).toBe("3");
  });

  it("omits fields that are absent from the diagnostics payload", () => {
    const rows = diagnosticRows({ detector: "claude_vision" });
    expect(rows.map((r) => r.label)).toEqual(["Detector"]);
  });
});
