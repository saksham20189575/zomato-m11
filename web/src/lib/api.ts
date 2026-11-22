import type { MetaResponse, RecommendRequest, ServiceResult } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function parseError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string | { msg?: string }[] };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      return data.detail[0].msg;
    }
  } catch {
    /* ignore */
  }
  return res.statusText || `Request failed (${res.status})`;
}

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await fetch(`${API_BASE}/meta`, { cache: "no-store" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<MetaResponse>;
}

export async function postRecommend(
  body: RecommendRequest,
): Promise<ServiceResult> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ServiceResult>;
}

export function matchPct(rank: number, rating: number): number {
  const base = 98 - (rank - 1) * 3;
  const nudge = Math.round((rating - 4.3) * 4);
  return Math.max(72, Math.min(99, base + Math.max(-3, Math.min(2, nudge))));
}

export function budgetDisplay(cost: number | null): string {
  if (cost == null) return "Budget n/a";
  const band = cost < 500 ? "₹ Low" : cost < 1200 ? "₹₹ Medium" : "₹₹₹ High";
  return `${band} (₹${Math.round(cost)} for 2)`;
}

export function cuisineTags(cuisine: string, explanation: string): string[] {
  const tags = cuisine
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 3);
  const extras: string[] = [];
  const lowered = explanation.toLowerCase();
  const hints: [string, string][] = [
    ["outdoor", "Outdoor Seating"],
    ["rooftop", "Rooftop"],
    ["craft", "Craft Drinks"],
    ["quiet", "Quiet"],
    ["family", "Family Friendly"],
    ["beer", "Craft Beer"],
    ["wine", "Wine"],
  ];
  for (const [needle, label] of hints) {
    if (lowered.includes(needle) && !tags.includes(label) && !extras.includes(label)) {
      extras.push(label);
    }
    if (extras.length >= 2) break;
  }
  return [...tags, ...extras].slice(0, 5);
}

export function sourceLabel(outcome: ServiceResult): string {
  if (!outcome.result) return "—";
  if (outcome.result.source === "fallback") return "Fallback · Local Signal";
  if (outcome.model_name === "mock") return "Mock LLM + Local Signal";
  return "AI LLM + Local Signal";
}

export const FEATURED_CUISINES = [
  "North Indian",
  "South Indian",
  "Chinese",
  "Italian",
  "Cafe",
  "Continental",
] as const;

export const DEMO_LOCATION_HINTS = [
  "Koramangala 5th Block, Bangalore",
  "Koramangala, Bangalore",
  "Indiranagar, Bangalore",
] as const;

export const DEMO_EXTRAS =
  "Rooftop ambience with outdoor seating and signature craft beverages";

export function pickDemoLocation(locations: string[]): string {
  for (const name of DEMO_LOCATION_HINTS) {
    if (locations.includes(name)) return name;
  }
  const bangalore = locations.find((l) =>
    l.toLowerCase().includes("bangalore"),
  );
  return bangalore ?? locations[0] ?? "Bangalore";
}

export function defaultLocation(locations: string[]): string {
  return pickDemoLocation(locations);
}
