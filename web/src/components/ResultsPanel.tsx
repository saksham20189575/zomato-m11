"use client";

import { sourceLabel } from "@/lib/api";
import type { ServiceResult, UiView } from "@/lib/types";
import { RecommendationCard } from "./RecommendationCard";

function LoadingSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-space-md">
      <div className="h-6 w-48 rounded bg-surface-container-high" />
      <div className="h-28 w-full rounded-xl bg-surface-container-low" />
      {[0, 1].map((i) => (
        <div
          key={i}
          className="flex h-32 w-full flex-col gap-3 rounded-xl bg-surface-container-low/70 p-4"
        >
          <div className="h-6 w-1/3 rounded bg-surface-container-high" />
          <div className="h-4 w-1/2 rounded bg-surface-container-high" />
          <div className="h-14 w-full rounded bg-surface-container-high/60" />
        </div>
      ))}
    </div>
  );
}

export function ResultsPanel({
  view,
  outcome,
  location,
  onRetry,
  onRelax,
}: {
  view: UiView;
  outcome: ServiceResult | null;
  location: string;
  onRetry: () => void;
  onRelax: () => void;
}) {
  if (view === "idle") {
    return (
      <section className="flex w-full flex-col gap-space-md lg:col-span-8">
        <div className="rounded-xl border border-white/[0.06] bg-surface-container-low/60 p-space-sm backdrop-blur-md">
          <p className="text-body-sm leading-tight text-on-surface-variant">
            Set preferences on the left, then hit{" "}
            <strong className="text-primary">Get recommendations</strong> — or
            load the Bangalore demo to preview the ranker.
          </p>
        </div>
      </section>
    );
  }

  if (view === "loading") {
    return (
      <section className="flex w-full flex-col gap-space-md lg:col-span-8">
        <div className="flex items-center justify-between px-space-xs">
          <span className="text-section-eyebrow font-semibold uppercase tracking-wider text-on-surface-variant">
            Results
          </span>
          <span className="text-label-sm text-primary-fixed-dim">
            Synthesizing live diner sentiments…
          </span>
        </div>
        <LoadingSkeleton />
      </section>
    );
  }

  if (view === "empty") {
    return (
      <section className="flex w-full flex-col gap-space-md lg:col-span-8">
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/[0.05] bg-surface-container-low/40 px-4 py-20 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-2xl text-primary">
            ⊘
          </div>
          <h3 className="font-headline text-headline-md text-on-surface">
            No matching culinary spots found
          </h3>
          <p className="mt-2 max-w-md text-body-md text-on-surface-variant">
            {outcome?.message ||
              "We couldn't find restaurants matching both the rating threshold and selected filters in this locality."}
          </p>
          <button
            type="button"
            onClick={onRelax}
            className="mt-6 rounded-full bg-primary-container px-6 py-2.5 text-label-lg text-white shadow-md transition-all hover:opacity-90"
          >
            Relax filter criteria
          </button>
        </div>
      </section>
    );
  }

  if (view === "error") {
    return (
      <section className="flex w-full flex-col gap-space-md lg:col-span-8">
        <div className="flex flex-col items-center justify-center rounded-2xl border border-error/20 bg-surface-container-low/40 px-4 py-20 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-error-container/30 text-2xl text-error">
            ☁
          </div>
          <h3 className="font-headline text-headline-md text-on-surface">
            TasteRank Engine Connection Failed
          </h3>
          <p className="mt-2 max-w-md text-body-md text-on-surface-variant">
            {outcome?.message ||
              "The local embedding vector store timed out. Please retry in a moment."}
          </p>
          <div className="mt-6 flex items-center gap-3">
            <button
              type="button"
              onClick={onRetry}
              className="rounded-full bg-primary-container px-6 py-2.5 text-label-lg text-white shadow-md transition-all hover:opacity-90"
            >
              Retry calculation
            </button>
          </div>
        </div>
      </section>
    );
  }

  // live
  const result = outcome?.result;
  const recs = result?.recommendations ?? [];
  const shortLoc = location.split(",")[0]?.trim() || location;
  const summary =
    result?.summary ||
    result?.note ||
    `Ranked ${recs.length} places near ${shortLoc} using your taste, budget, and rating bar.`;

  return (
    <section className="flex w-full flex-col gap-space-md lg:col-span-8">
      <div className="flex items-center justify-between px-space-xs">
        <span className="text-section-eyebrow font-semibold uppercase tracking-wider text-on-surface-variant">
          Results
        </span>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-ping rounded-full bg-primary" />
          <span className="text-label-sm text-primary-fixed-dim">
            Grounded shortlist · {outcome?.shortlist_size ?? 0} candidates
          </span>
        </div>
      </div>

      <div className="flex items-center gap-space-sm rounded-xl border border-white/[0.06] bg-surface-container-low/60 p-space-sm backdrop-blur-md">
        <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs text-primary">
          ✓
        </div>
        <p className="text-body-sm leading-tight text-on-surface-variant">
          Evaluated with TasteRank Multi-factor Ranker. Cross-referenced with
          local sentiment, footfall patterns, and seasonal kitchen quality.
        </p>
      </div>

      <div className="relative flex flex-col gap-space-sm overflow-hidden rounded-xl border border-white/[0.08] bg-gradient-to-br from-surface-container-low/80 to-surface-container/60 p-space-md shadow-xl">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-headline text-headline-md text-on-surface">
              Top matches for {shortLoc}
            </h2>
            <span className="rounded-full border border-white/[0.08] bg-white/[0.06] px-2 py-0.5 text-label-sm text-on-surface-variant">
              {recs.length} places found
            </span>
          </div>
          {outcome && (
            <div className="flex items-center gap-1.5 self-start rounded-full border border-white/[0.05] bg-surface-container-highest/80 px-2.5 py-1 sm:self-auto">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span className="text-label-sm text-on-surface">
                {sourceLabel(outcome)}
              </span>
            </div>
          )}
        </div>
        <div className="mt-1 rounded-lg border-l-2 border-primary-container bg-surface-container-lowest/60 p-3 text-body-sm leading-relaxed text-on-surface-variant">
          <span className="mb-0.5 block text-label-md font-semibold text-primary">
            Synthesis:
          </span>
          {summary}
        </div>
      </div>

      <div className="flex flex-col gap-space-md">
        {recs.map((rec) => (
          <RecommendationCard key={`${rec.restaurant_id}-${rec.rank}`} rec={rec} />
        ))}
      </div>
    </section>
  );
}
