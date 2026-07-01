// Central UI sport registry. Single source of truth for which sports the UI
// supports, how they present, and whether each has full AI support or is a
// preview/experimental sport. Pairs with sportLabel() in ./sportEvidence.

import { Circle, CircleDot, Target, Trophy, type LucideIcon } from "lucide-react";

export type SupportLevel = "full" | "preview";

export interface SportConfig {
  id: string;
  name: string;
  Icon: LucideIcon;
  /** "full" = complete AI rules/perception; "preview" = experimental, rules not yet configured. */
  supportLevel: SupportLevel;
  levels: string[];
  leaguePlaceholder: string;
  callPlaceholder: string;
  /** Sport-specific rulebook label used in copy/loading steps. */
  rulebookName: string;
}

const GENERIC_LEVELS = [
  "Professional",
  "College / University",
  "High School",
  "Youth",
  "Rec League",
  "Other",
];

export const SPORTS: SportConfig[] = [
  {
    id: "basketball",
    name: "Basketball",
    Icon: Trophy,
    supportLevel: "full",
    levels: [
      "Professional",
      "College / University",
      "High School",
      "Youth / AAU",
      "Rec League",
      "Pickup / Street",
      "Other",
    ],
    leaguePlaceholder: "e.g., NBA, NCAA, FIBA, EuroLeague, local rec league",
    callPlaceholder: "e.g., Blocking foul, Traveling, Out of bounds",
    rulebookName: "basketball rulebook",
  },
  {
    id: "hockey",
    name: "Hockey",
    Icon: CircleDot,
    supportLevel: "preview",
    levels: GENERIC_LEVELS,
    leaguePlaceholder: "e.g., NHL, IIHF, junior league",
    callPlaceholder: "e.g., Tripping, Offside, High-sticking",
    rulebookName: "hockey rulebook",
  },
  {
    id: "soccer",
    name: "Soccer",
    Icon: Circle,
    supportLevel: "preview",
    levels: GENERIC_LEVELS,
    leaguePlaceholder: "e.g., FIFA, Premier League, MLS",
    callPlaceholder: "e.g., Handball, Offside, Penalty",
    rulebookName: "soccer rulebook",
  },
  {
    id: "lacrosse",
    name: "Lacrosse",
    Icon: Target,
    supportLevel: "preview",
    levels: GENERIC_LEVELS,
    leaguePlaceholder: "e.g., NLL, NCAA, club league",
    callPlaceholder: "e.g., Slashing, Crease violation, Warding",
    rulebookName: "lacrosse rulebook",
  },
];

export const DEFAULT_SPORT_ID = "basketball";

const SPORTS_BY_ID: Record<string, SportConfig> = Object.fromEntries(
  SPORTS.map((sport) => [sport.id, sport]),
);

/** Look up a sport config; falls back to the default sport for unknown ids. */
export function getSport(id: string): SportConfig {
  return SPORTS_BY_ID[(id || "").toLowerCase().trim()] ?? SPORTS_BY_ID[DEFAULT_SPORT_ID];
}

/** True when the sport is experimental (AI rules not yet fully configured). */
export function isPreviewSport(id: string): boolean {
  const sport = SPORTS_BY_ID[(id || "").toLowerCase().trim()];
  return sport ? sport.supportLevel === "preview" : false;
}
