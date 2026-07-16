// Shared referee directory (Sprint 8).
//
// Single source of truth for the demo referee roster + the `/ref/<slug>` slug
// helper (previously duplicated in Leaderboard, RefLeaderboards, and Feed, and
// the RefProfile screen ignored the slug entirely and always showed one ref).
//
// These are illustrative demo profiles for the hackathon build — real NBA names
// with representative, not-official ratings.
import type { StaticImageData } from "next/image";

import edMalloyPhoto from "../images/ed_malloy.jpg";
import jamesCapersPhoto from "../images/james_capers.jpg";
import johnGoblePhoto from "../images/john_goble.jpg";
import marcDavisPhoto from "../images/marc_davis.jpg";
import scottFosterPhoto from "../images/scott_foster.jpg";
import tonyBrothersPhoto from "../images/Tony-Brothers-scaled.jpg";
import zachZarbaPhoto from "../images/zach_zarba.jpg";

export interface Referee {
  rank: number;
  name: string;
  league: string;
  sport: string;
  years: number;
  rating: number;
  totalRatings: number;
  aiCallsAnalyzed: number;
  aiAgreement: number;
  trend: "up" | "neutral" | "down";
  photo: StaticImageData;
}

/** URL slug for a referee name, e.g. "Scott Foster" -> "scott-foster". */
export const refSlug = (name: string): string =>
  name.toLowerCase().replace(/\s+/g, "-");

export const REFEREES: Referee[] = [
  { rank: 1, name: "Zach Zarba", league: "NBA", sport: "Basketball", years: 22, rating: 4.8, totalRatings: 2418, aiCallsAnalyzed: 173, aiAgreement: 86, trend: "up", photo: zachZarbaPhoto },
  { rank: 2, name: "Marc Davis", league: "NBA", sport: "Basketball", years: 27, rating: 4.7, totalRatings: 2675, aiCallsAnalyzed: 218, aiAgreement: 84, trend: "up", photo: marcDavisPhoto },
  { rank: 3, name: "John Goble", league: "NBA", sport: "Basketball", years: 17, rating: 4.6, totalRatings: 1984, aiCallsAnalyzed: 151, aiAgreement: 82, trend: "neutral", photo: johnGoblePhoto },
  { rank: 4, name: "Ed Malloy", league: "NBA", sport: "Basketball", years: 23, rating: 4.5, totalRatings: 2261, aiCallsAnalyzed: 150, aiAgreement: 80, trend: "up", photo: edMalloyPhoto },
  { rank: 5, name: "James Capers", league: "NBA", sport: "Basketball", years: 30, rating: 4.4, totalRatings: 2517, aiCallsAnalyzed: 204, aiAgreement: 79, trend: "neutral", photo: jamesCapersPhoto },
  { rank: 6, name: "Tony Brothers", league: "NBA", sport: "Basketball", years: 27, rating: 3.3, totalRatings: 3142, aiCallsAnalyzed: 216, aiAgreement: 64, trend: "down", photo: tonyBrothersPhoto },
  { rank: 7, name: "Scott Foster", league: "NBA", sport: "Basketball", years: 31, rating: 3.1, totalRatings: 3898, aiCallsAnalyzed: 262, aiAgreement: 61, trend: "down", photo: scottFosterPhoto },
];

/** Look up a referee by URL slug; returns null when no roster entry matches. */
export function getRefBySlug(slug: string): Referee | null {
  return REFEREES.find((ref) => refSlug(ref.name) === slug) ?? null;
}
