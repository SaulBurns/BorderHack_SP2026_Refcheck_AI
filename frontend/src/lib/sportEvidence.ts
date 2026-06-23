// Sport-aware evidence rendering (Phase 3 of the sport-agnostic perception plan).
//
// Pure, framework-free logic so it is unit-testable in isolation. Verdict.tsx
// composes the sport-specific rows returned here between its neutral rows.
//
// Backward compatibility: each sport reads from `perception.sport_details[sport]`
// first and falls back to the legacy top-level fields, so basketball renders
// exactly as it did before the migration whether or not the backend has been
// upgraded.

import type { EventDescription } from "./types";

export interface EvidenceRow {
  label: string;
  value: boolean;
  detail: string;
}

const humanize = (value: string | undefined): string =>
  value ? value.replace(/_/g, " ") : "unclear";

function basketballRows(p: EventDescription): EvidenceRow[] {
  const details = p.sport_details?.basketball;
  // Prefer sport_details; fall back to legacy top-level fields (back-compat).
  const courtGeometry = details?.court_geometry ?? p.court_geometry;
  const defenderStatus = details?.defender_status ?? p.defender_status;
  const keyZone = courtGeometry?.key_zone;
  const legalGuardingPosition = defenderStatus?.legal_guarding_position;

  return [
    {
      label: "Court zone known",
      // Identical semantics to the pre-migration Verdict.tsx logic.
      value: Boolean(keyZone && keyZone !== "backcourt_or_unclear"),
      detail: keyZone?.replace(/_/g, " ") || "unclear",
    },
    {
      label: "Defender status",
      value: legalGuardingPosition !== "unclear",
      detail: legalGuardingPosition?.replace(/_/g, " ") || "unclear",
    },
  ];
}

function hockeyRows(p: EventDescription): EvidenceRow[] {
  const d = p.sport_details?.hockey;
  return [
    {
      label: "Zone identified",
      value: Boolean(d && d.zone !== "unclear"),
      detail: humanize(d?.zone),
    },
    {
      label: "Goalie involved",
      value: Boolean(d?.goalie_involved),
      detail: d?.goalie_involved ? "yes" : "no",
    },
  ];
}

function soccerRows(p: EventDescription): EvidenceRow[] {
  const d = p.sport_details?.soccer;
  return [
    {
      label: "Field third known",
      value: Boolean(d && d.field_third !== "unclear"),
      detail: humanize(d?.field_third),
    },
    {
      label: "In penalty area",
      value: Boolean(d?.in_penalty_area),
      detail: d?.in_penalty_area ? "yes" : "no",
    },
  ];
}

function lacrosseRows(p: EventDescription): EvidenceRow[] {
  const d = p.sport_details?.lacrosse;
  return [
    {
      label: "Ball carrier status",
      value: Boolean(d && d.ball_carrier_status !== "unclear"),
      detail: humanize(d?.ball_carrier_status),
    },
    {
      label: "Crease violation",
      value: Boolean(d?.crease_violation),
      detail: d?.crease_violation ? "yes" : "no",
    },
  ];
}

const SPORT_EVIDENCE: Record<string, (p: EventDescription) => EvidenceRow[]> = {
  basketball: basketballRows,
  hockey: hockeyRows,
  soccer: soccerRows,
  lacrosse: lacrosseRows,
};

/**
 * Sport-specific evidence rows for the verdict review checklist.
 * Unknown sports return [] so the UI degrades gracefully.
 */
export function sportEvidenceRows(
  sport: string,
  perception: EventDescription,
): EvidenceRow[] {
  const fn = SPORT_EVIDENCE[(sport || "").toLowerCase().trim()];
  return fn ? fn(perception) : [];
}

/** Display label for a sport id, e.g. "basketball" -> "Basketball". */
export function sportLabel(sport: string): string {
  if (!sport) return "Unknown";
  return sport.charAt(0).toUpperCase() + sport.slice(1);
}
