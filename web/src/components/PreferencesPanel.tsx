"use client";

import { FEATURED_CUISINES } from "@/lib/api";
import type { BudgetBand } from "@/lib/types";

const ANY = "Any cuisine";

const BUDGET_OPTIONS: { value: BudgetBand; label: string }[] = [
  { value: "low", label: "₹ Low" },
  { value: "medium", label: "₹₹ Medium" },
  { value: "high", label: "₹₹₹ High" },
];

export interface PrefsState {
  location: string;
  cuisine: string;
  budget: BudgetBand;
  minRating: number;
  topK: number;
  extras: string;
  mock: boolean;
}

export function PreferencesPanel({
  prefs,
  locations,
  cuisines,
  loading,
  onChange,
  onSubmit,
  onDemo,
  onReset,
}: {
  prefs: PrefsState;
  locations: string[];
  cuisines: string[];
  loading: boolean;
  onChange: (patch: Partial<PrefsState>) => void;
  onSubmit: () => void;
  onDemo: () => void;
  onReset: () => void;
}) {
  const featured: string[] = FEATURED_CUISINES.filter((c) =>
    cuisines.includes(c),
  );
  const chipOptions = [ANY, ...featured];

  return (
    <aside className="flex w-full flex-col gap-space-md lg:col-span-4">
      <div className="flex items-center justify-between px-space-xs">
        <span className="text-section-eyebrow font-semibold uppercase tracking-wider text-on-surface-variant">
          Preferences
        </span>
        <button
          type="button"
          onClick={onReset}
          className="text-label-sm text-primary transition-opacity hover:opacity-80"
        >
          Reset Filters
        </button>
      </div>

      <div className="relative flex flex-col gap-space-md overflow-hidden rounded-xl border border-white/[0.08] bg-surface-container-low/70 p-space-md shadow-2xl backdrop-blur-xl">
        <div className="pointer-events-none absolute -right-16 -top-16 h-32 w-32 rounded-full bg-primary-container/10 blur-2xl" />

        <div className="flex flex-col gap-1.5">
          <label className="text-label-sm font-medium text-on-surface-variant">
            Neighborhood or City
          </label>
          <div className="relative flex items-center">
            <span className="absolute left-3 text-[14px] text-primary">📍</span>
            <select
              className="w-full appearance-none rounded-lg border border-white/[0.08] bg-surface-container-lowest/90 py-2 pl-9 pr-3 text-body-sm text-on-surface transition-all focus:border-primary-container focus:outline-none focus:ring-1 focus:ring-primary-container/40"
              value={prefs.location}
              onChange={(e) => onChange({ location: e.target.value })}
            >
              {locations.map((loc) => (
                <option key={loc} value={loc}>
                  {loc}
                </option>
              ))}
            </select>
          </div>
          <span className="text-label-sm text-outline">
            Targeting Koramangala, Indiranagar, and CBD
          </span>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-label-sm font-medium text-on-surface-variant">
            Cuisines of Interest
          </label>
          <div className="flex flex-wrap gap-1.5">
            {chipOptions.map((chip) => {
              const selected = prefs.cuisine === chip;
              return (
                <button
                  key={chip}
                  type="button"
                  onClick={() => onChange({ cuisine: chip })}
                  className={`rounded-full border px-2.5 py-1 text-label-sm transition-all ${
                    selected
                      ? "border-primary/50 bg-primary/20 text-primary"
                      : "border-white/[0.06] bg-white/[0.04] text-on-surface-variant hover:bg-white/[0.08]"
                  }`}
                >
                  {chip}
                </button>
              );
            })}
          </div>
          {cuisines.length > featured.length && (
            <select
              className="mt-1 w-full rounded-lg border border-white/[0.08] bg-surface-container-lowest/90 px-3 py-2 text-body-sm text-on-surface focus:border-primary-container focus:outline-none"
              value={
                chipOptions.includes(prefs.cuisine as (typeof chipOptions)[number])
                  ? ""
                  : prefs.cuisine
              }
              onChange={(e) => {
                if (e.target.value) onChange({ cuisine: e.target.value });
              }}
            >
              <option value="">More cuisines…</option>
              {cuisines
                .filter((c) => !featured.includes(c))
                .map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
            </select>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-label-sm font-medium text-on-surface-variant">
            Estimated Budget
          </label>
          <div className="grid grid-cols-3 rounded-lg border border-white/[0.06] bg-surface-container-lowest/90 p-1">
            {BUDGET_OPTIONS.map((opt) => {
              const selected = prefs.budget === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => onChange({ budget: opt.value })}
                  className={`rounded-md py-1.5 text-center text-label-sm transition-all ${
                    selected
                      ? "border border-primary-container/30 bg-primary-container/20 font-medium text-primary"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label className="text-label-sm font-medium text-on-surface-variant">
              Minimum Diner Rating
            </label>
            <span className="text-label-sm font-semibold text-primary">
              {prefs.minRating.toFixed(1)} ★
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={5}
            step={0.1}
            value={prefs.minRating}
            onChange={(e) =>
              onChange({ minRating: Number.parseFloat(e.target.value) })
            }
            className="h-1.5 w-full cursor-pointer rounded-lg bg-surface-container-high"
          />
          <div className="flex justify-between text-label-sm text-outline">
            <span>0★</span>
            <span>4.5★ Exceptional</span>
            <span>5.0★</span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-1">
          <div className="flex flex-col">
            <label className="text-label-sm font-medium text-on-surface">
              Number of picks (Top-K)
            </label>
            <span className="text-label-sm text-outline">
              Grounded top matches
            </span>
          </div>
          <div className="flex items-center rounded-full border border-white/[0.08] bg-surface-container-lowest p-1">
            <button
              type="button"
              className="flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-all hover:bg-white/[0.08] active:scale-95"
              onClick={() =>
                onChange({ topK: Math.max(1, prefs.topK - 1) })
              }
            >
              −
            </button>
            <span className="w-8 text-center text-label-md font-semibold text-primary">
              {prefs.topK}
            </span>
            <button
              type="button"
              className="flex h-7 w-7 items-center justify-center rounded-full text-on-surface-variant transition-all hover:bg-white/[0.08] active:scale-95"
              onClick={() =>
                onChange({ topK: Math.min(20, prefs.topK + 1) })
              }
            >
              +
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-label-sm font-medium text-on-surface-variant">
            Specific Vibes or Dietary Notes
          </label>
          <textarea
            rows={3}
            value={prefs.extras}
            onChange={(e) => onChange({ extras: e.target.value })}
            placeholder="e.g. rooftop seating, pet friendly, craft beer on tap…"
            className="w-full resize-none rounded-lg border border-white/[0.08] bg-surface-container-lowest/90 p-2.5 text-body-sm text-on-surface transition-all placeholder:text-outline focus:border-primary-container focus:outline-none focus:ring-1 focus:ring-primary-container/40"
          />
        </div>

        <label className="flex cursor-pointer items-center gap-2 text-label-sm text-on-surface-variant">
          <input
            type="checkbox"
            checked={prefs.mock}
            onChange={(e) => onChange({ mock: e.target.checked })}
            className="h-4 w-4 rounded border-outline accent-primary-container"
          />
          Mock LLM (offline)
        </label>

        <div className="flex flex-col gap-2 pt-2">
          <button
            type="button"
            disabled={loading || !prefs.location}
            onClick={onSubmit}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-gradient-to-r from-primary-container to-secondary py-2.5 text-label-lg text-white shadow-lg shadow-primary-container/20 transition-all hover:opacity-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span>✦</span>
            <span>{loading ? "Ranking local tastes…" : "Get recommendations"}</span>
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={onDemo}
            className="w-full rounded-full border border-white/[0.08] bg-white/[0.03] py-2 text-label-md text-on-surface transition-all hover:bg-white/[0.06] disabled:opacity-50"
          >
            Try Bangalore Demo (Koramangala & Indiranagar)
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-xl border border-white/[0.04] bg-surface-container-low/40 p-3">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          ◈
        </div>
        <div className="flex flex-col">
          <span className="text-label-md font-medium text-on-surface">
            Bangalore Local Ranker v4.2
          </span>
          <span className="text-body-sm text-on-surface-variant">
            {locations.length} locations · {cuisines.length} cuisines
          </span>
        </div>
      </div>
    </aside>
  );
}
