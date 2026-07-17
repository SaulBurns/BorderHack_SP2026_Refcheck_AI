// Central UI sport registry. Single source of truth for which sports the UI
// supports, how they present, and the sport-aware vocabulary the reasoning
// overlay uses. Every registered sport has full AI support (backend Sprints
// 10-12 + the self-contained refactor). Pairs with sportLabel() in ./sportEvidence.

import { Circle, CircleDot, Target, Trophy, type LucideIcon } from "lucide-react";

/** Sport-aware labels for the AI reasoning overlay markers. */
export interface SportOverlayVocab {
  /** Primary player in possession (e.g. "Ball handler", "Puck carrier"). */
  offense: string;
  /** Additional attacking players. */
  offenseSecondary: string;
  /** Primary defender. */
  defense: string;
  /** Additional defenders. */
  defenseSecondary: string;
  /** The object of play (e.g. "Ball", "Puck"). */
  object: string;
}

export interface SportConfig {
  id: string;
  name: string;
  Icon: LucideIcon;
  levels: string[];
  leaguePlaceholder: string;
  callPlaceholder: string;
  /** Sport-specific rulebook label used in copy/loading steps. */
  rulebookName: string;
  /** Vocabulary the reasoning overlay uses for this sport. */
  overlay: SportOverlayVocab;
}

const GENERIC_LEVELS = [
  "Professional",
  "College / University",
  "High School",
  "Youth",
  "Rec League",
  "Other",
];

/** Neutral overlay vocabulary for a sport the UI does not know statically. */
export const GENERIC_OVERLAY: SportOverlayVocab = {
  offense: "Attacker",
  offenseSecondary: "Support",
  defense: "Defender",
  defenseSecondary: "Cover defender",
  object: "Ball",
};

export const SPORTS: SportConfig[] = [
  {
    id: "basketball",
    name: "Basketball",
    Icon: Trophy,
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
    overlay: {
      offense: "Ball handler",
      offenseSecondary: "Off-ball offense",
      defense: "Defender",
      defenseSecondary: "Help defense",
      object: "Ball",
    },
  },
  {
    id: "soccer",
    name: "Soccer",
    Icon: Circle,
    levels: GENERIC_LEVELS,
    leaguePlaceholder: "e.g., FIFA, Premier League, MLS",
    callPlaceholder: "e.g., Handball, Offside, Penalty",
    rulebookName: "soccer rulebook",
    overlay: {
      offense: "Attacker",
      offenseSecondary: "Support runner",
      defense: "Defender",
      defenseSecondary: "Cover defender",
      object: "Ball",
    },
  },
  {
    id: "hockey",
    name: "Hockey",
    Icon: CircleDot,
    levels: GENERIC_LEVELS,
    leaguePlaceholder: "e.g., NHL, IIHF, junior league",
    callPlaceholder: "e.g., Tripping, Offside, High-sticking",
    rulebookName: "hockey rulebook",
    overlay: {
      offense: "Puck carrier",
      offenseSecondary: "Forward",
      defense: "Defender",
      defenseSecondary: "Backchecker",
      object: "Puck",
    },
  },
  {
    id: "lacrosse",
    name: "Lacrosse",
    Icon: Target,
    levels: GENERIC_LEVELS,
    leaguePlaceholder: "e.g., NLL, NCAA, club league",
    callPlaceholder: "e.g., Slashing, Crease violation, Warding",
    rulebookName: "lacrosse rulebook",
    overlay: {
      offense: "Ball carrier",
      offenseSecondary: "Cutter",
      defense: "Defender",
      defenseSecondary: "Slide defender",
      object: "Ball",
    },
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

/** Overlay vocabulary for a sport; a neutral default for unknown sports. */
export function overlayVocab(id: string): SportOverlayVocab {
  return SPORTS_BY_ID[(id || "").toLowerCase().trim()]?.overlay ?? GENERIC_OVERLAY;
}
