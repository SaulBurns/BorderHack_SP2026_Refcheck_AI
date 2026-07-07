// src/lib/types.ts
// Mirrors backend/app/models/schemas.py — keep them in sync.

export type Verdict = "fair_call" | "bad_call" | "inconclusive";
export type VisualQuality = "clear" | "partial" | "obstructed" | "poor";
export type PlayerRole = "offense" | "defense" | "unclear";

export interface PlayerObservation {
  role: PlayerRole;
  jersey_color: string | null;
  position_description: string;
  court_zone?: string;
  body_state: string;
}

// --- Sport-specific perception detail blocks (mirror backend perception_schema.py) ---

export interface DefenderStatus {
  primary_or_secondary: string;
  legal_guarding_position: string;
  feet_set_before_contact: boolean;
  moving_direction: string;
  inside_restricted_area: boolean;
}

export interface CourtGeometry {
  key_zone: string;
  restricted_area_arc_visible: boolean;
  defender_feet_visible: boolean;
  basket_visible: boolean;
}

export interface BasketballDetails {
  offensive_control_status: string;
  defender_status: DefenderStatus;
  court_geometry: CourtGeometry;
}

export interface HockeyDetails {
  zone: string;
  goalie_involved: boolean;
  puck_possession: string;
  infraction_candidate: string;
  boards_involved: boolean;
}

export interface SoccerDetails {
  field_third: string;
  in_penalty_area: boolean;
  offside_relevant: boolean;
  last_defender: boolean;
  handball_candidate: boolean;
  foul_direction: string;
}

export interface LacrosseDetails {
  crease_violation: boolean;
  cross_check: boolean;
  slashing: boolean;
  ball_carrier_status: string;
  warding: boolean;
}

export type SportDetails =
  | BasketballDetails
  | HockeyDetails
  | SoccerDetails
  | LacrosseDetails;

// Backend emits sport_details keyed by sport name (e.g. sport_details.basketball).
export interface SportDetailsMap {
  basketball?: BasketballDetails;
  hockey?: HockeyDetails;
  soccer?: SoccerDetails;
  lacrosse?: LacrosseDetails;
}

export interface EventDescription {
  schema_version?: number;
  sport: string;
  event_type: string;
  summary: string;
  players_involved: PlayerObservation[];
  contact_detected: boolean;
  contact_location: string;
  ball_visible: boolean;
  ball_state: string;
  // Legacy basketball-specific fields. Kept for backward compatibility during the
  // sport_details migration; prefer reading from `sport_details` (see Phase 3).
  offensive_control_status?: string;
  defender_status?: DefenderStatus;
  court_geometry?: CourtGeometry;
  frame_observations?: Array<{
    frame_index: number;
    approx_time_seconds: number;
    observation: string;
  }>;
  moment_of_interest_seconds: number | null;
  impact_zone?: {
    x_percent: number;
    y_percent: number;
    radius_percent: number;
    label: string;
  };
  visual_quality: VisualQuality;
  perception_confidence: number;
  sport_details?: SportDetailsMap;
  notes: string | null;
}

export interface RuleChunk {
  rule_id: string;
  section_title: string;
  text: string;
  page_number: number;
  similarity_score: number;
}

export interface AdjudicatorOutput {
  verdict: Verdict;
  confidence: number;
  primary_rule_id: string | null;
  reasoning: string;
  flags: string[];
}

export interface FinalVerdict {
  verdict: Verdict;
  confidence: number;
  reasoning: string;
  cited_rule: RuleChunk | null;
  perception: EventDescription;
  adjudicator_a: AdjudicatorOutput;
  adjudicator_b: AdjudicatorOutput;
  reconciliation_note: string;
  processing_time_seconds: number;
}

// --- Optional NBA game-context enrichment (basketball only, Phase 10A) ---

export type GameResolutionStatus =
  | "resolved"
  | "candidate_match"
  | "unresolved"
  | "skipped";

export interface GameCandidate {
  provider: "nba";
  game_id: string;
  game_date?: string | null;
  home_team?: string | null;
  away_team?: string | null;
  home_team_code?: string | null;
  away_team_code?: string | null;
  status_text?: string | null;
  confidence?: number | null;
  match_reasons: string[];
}

export interface GameContext {
  provider: "nba";
  game_id?: string | null;
  game_date?: string | null;
  home_team?: string | null;
  away_team?: string | null;
  home_team_code?: string | null;
  away_team_code?: string | null;
  season?: string | null;
  quarter?: string | null;
  clock?: string | null;
  score_summary?: string | null;
  resolution_status: GameResolutionStatus;
  confidence?: number | null;
  match_reasons: string[];
  candidates?: GameCandidate[];
}

export interface AnalyzeResponse {
  verdict: FinalVerdict;
  clip_id: string;
  clip_url?: string;
  key_moment?: {
    frame_url: string;
    frame_number: number;
    approximate_seconds: number | null;
    title: string;
    explanation: string;
  };
  // Additive; present only for basketball clips.
  game_context?: GameContext;
}

// Display helpers
export const VERDICT_LABEL: Record<Verdict, string> = {
  fair_call: "FAIR CALL",
  bad_call: "BAD CALL",
  inconclusive: "INCONCLUSIVE",
};

export const VERDICT_COLOR: Record<Verdict, string> = {
  fair_call: "#2DBF4F",
  bad_call: "#E63946",
  inconclusive: "#F6B40F",
};
