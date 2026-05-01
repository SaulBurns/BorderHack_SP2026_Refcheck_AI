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
