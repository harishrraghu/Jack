import type { AnalysisResponse, FeedbackMetrics, JournalEntry } from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getAnalysis(timeframe: string) {
  return readJson<AnalysisResponse>(`/api/analysis?timeframe=${timeframe}`);
}

export function getJournal() {
  return readJson<JournalEntry[]>("/api/journal");
}

export function getFeedback() {
  return readJson<FeedbackMetrics>("/api/feedback");
}

