// Dynamic, sport-agnostic rendering of a sport's `sport_details` block and the
// analysis diagnostics. Pure, framework-free logic so it is unit-testable.
//
// The backend exposes each sport's structured signals under
// `perception.sport_details[<sport>]` (basketball, soccer, hockey, lacrosse, or a
// future plugin). Rather than hardcode a renderer per sport, we walk whatever
// fields the block contains and present them generically — so a brand-new backend
// sport renders with no frontend change. This mirrors the backend's self-contained
// Sport plugin architecture.

import type { Diagnostics, EventDescription } from "./types";

export interface DetailRow {
  label: string;
  value: boolean;
  detail: string;
}

/** "field_third" -> "Field third". */
export function humanizeKey(key: string): string {
  const spaced = key.replace(/_/g, " ").trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : "";
}

const humanizeValue = (value: string): string => value.replace(/_/g, " ").trim();

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function fieldRows(key: string, value: unknown): DetailRow[] {
  if (typeof value === "boolean") {
    return [{ label: humanizeKey(key), value, detail: value ? "yes" : "no" }];
  }
  if (typeof value === "string") {
    const detail = humanizeValue(value) || "unclear";
    return [{ label: humanizeKey(key), value: value !== "" && value !== "unclear", detail }];
  }
  if (typeof value === "number") {
    return [{ label: humanizeKey(key), value: true, detail: String(value) }];
  }
  if (isPlainObject(value)) {
    // Flatten nested blocks (e.g. basketball defender_status / court_geometry) so
    // every leaf signal shows as its own row.
    return Object.entries(value).flatMap(([childKey, childValue]) =>
      fieldRows(childKey, childValue),
    );
  }
  return [];
}

/**
 * Render every field of `perception.sport_details[sport]` as a labeled row.
 * Returns [] when the sport has no detail block, so the UI degrades gracefully.
 * Works for any sport, including one the frontend does not know statically.
 */
export function dynamicSportDetailRows(
  sport: string,
  perception: EventDescription,
): DetailRow[] {
  const key = (sport || "").toLowerCase().trim();
  const block = perception.sport_details?.[key];
  if (!isPlainObject(block)) return [];
  return Object.entries(block).flatMap(([fieldKey, value]) => fieldRows(fieldKey, value));
}

// --- Diagnostics / tracked-evidence rows -----------------------------------

// Curated, sport-agnostic ordering of the diagnostics worth surfacing to a
// reviewer. Only fields actually present in the payload are rendered.
const DIAGNOSTIC_FIELDS: Array<{ key: keyof Diagnostics; label: string }> = [
  { key: "provider_used", label: "Provider" },
  { key: "detector", label: "Detector" },
  { key: "fallback_reason", label: "Fallback reason" },
  { key: "detections_present", label: "Detections present" },
  { key: "player_count", label: "Players tracked" },
  { key: "ball_present", label: "Ball tracked" },
  { key: "tracked_evidence_present", label: "Tracked evidence present" },
  { key: "tracking_confidence", label: "Tracking confidence" },
  { key: "possession_summary", label: "Possession summary" },
  { key: "yolo_influenced", label: "Tracking influenced verdict" },
  { key: "ball_trajectory_present", label: "Ball trajectory present" },
  { key: "influenced_reconciliation", label: "Influenced reconciliation" },
];

function diagnosticRow(label: string, value: unknown): DetailRow | null {
  if (value === undefined || value === null || value === "") return null;
  if (typeof value === "boolean") {
    return { label, value, detail: value ? "yes" : "no" };
  }
  if (typeof value === "number") {
    // Confidences are 0-1; render as a percentage. Counts render as-is.
    const detail =
      label.toLowerCase().includes("confidence") && value <= 1
        ? `${Math.round(value * 100)}%`
        : String(value);
    return { label, value: value > 0, detail };
  }
  const text = String(value);
  return { label, value: text !== "" && text !== "unclear", detail: humanizeValue(text) };
}

/**
 * Sport-agnostic diagnostic rows (detector/provider, tracked evidence, tracking
 * confidence, possession, YOLO influence). Returns [] when diagnostics are absent.
 */
export function diagnosticRows(diagnostics: Diagnostics | undefined): DetailRow[] {
  if (!diagnostics) return [];
  return DIAGNOSTIC_FIELDS.flatMap(({ key, label }) => {
    const row = diagnosticRow(label, diagnostics[key]);
    return row ? [row] : [];
  });
}
