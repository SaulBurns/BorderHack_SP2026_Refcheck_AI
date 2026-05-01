// src/lib/api.ts
import type { AnalyzeResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface AnalyzeParams {
  file: File;
  sport: "basketball";
  originalCall?: string;
  refName?: string;
  league?: string;
  level?: string;
}

export async function analyzeClip(
  params: AnalyzeParams,
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append("file", params.file);
  formData.append("sport", params.sport);
  if (params.originalCall) formData.append("original_call", params.originalCall);
  if (params.refName) formData.append("ref_name", params.refName);
  if (params.league) formData.append("league", params.league);
  if (params.level) formData.append("level", params.level);

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Analysis failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export interface FeedItem {
  clip_id: string;
  video_url: string | null;
  league: string | null;
  level_of_play: string | null;
  original_call: string | null;
  referee_name: string | null;
  verdict: "fair_call" | "bad_call" | "inconclusive" | string | null;
  confidence: number | null;
  call_type: string | null;
  rule_id: string | null;
  reasoning: string | null;
  created_at: string;
  votes_fair: number;
  votes_bad: number;
  votes_inconclusive: number;
}

export async function getFeedItems(): Promise<FeedItem[]> {
  const res = await fetch(`${API_BASE}/api/feed?limit=20`, {
    cache: "no-store",
  });

  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data.items) ? data.items : [];
}

export function resolveApiUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  return `${API_BASE}${pathOrUrl}`;
}

// Local persistence helpers — simple sessionStorage cache so the verdict page
// can re-render without re-hitting the API.
export function cacheVerdict(clipId: string, response: AnalyzeResponse): void {
  sessionStorage.setItem(`refcheck:verdict:${clipId}`, JSON.stringify(response));
}

export function getCachedVerdict(clipId: string): AnalyzeResponse | null {
  const raw = sessionStorage.getItem(`refcheck:verdict:${clipId}`);
  return raw ? (JSON.parse(raw) as AnalyzeResponse) : null;
}

// Persists the local blob URL (from URL.createObjectURL) for the uploaded video
// so the verdict page can replay it without re-uploading.
export function cacheLocalVideoUrl(clipId: string, blobUrl: string): void {
  sessionStorage.setItem(`refcheck:localvideo:${clipId}`, blobUrl);
}

export function getCachedLocalVideoUrl(clipId: string): string | null {
  return sessionStorage.getItem(`refcheck:localvideo:${clipId}`);
}
