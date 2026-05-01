// src/lib/types.ts
// Mirrors backend/app/models/schemas.py — keep them in sync.

export type Verdict = "fair_call" | "bad_call" | "inconclusive";
export type VisualQuality = "clear" | "partial" | "obstructed" | "poor";
export type PlayerRole = "offense" | "defense" | "unclear";

export interface PlayerObservation {
  role: PlayerRole;
  jersey_color: string | null;
  position_description: string;
  body_state: string;
}

export interface EventDescription {
  sport: "basketball";
  event_type: string;
  summary: string;
  players_involved: PlayerObservation[];
  contact_detected: boolean;
  contact_location: string;
  ball_visible: boolean;
  ball_state: string;
  moment_of_interest_seconds: number | null;
  visual_quality: VisualQuality;
  perception_confidence: number;
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
