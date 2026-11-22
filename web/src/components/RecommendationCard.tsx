import { budgetDisplay, cuisineTags, matchPct } from "@/lib/api";
import type { Recommendation } from "@/lib/types";

export function RecommendationCard({ rec }: { rec: Recommendation }) {
  const match = matchPct(rec.rank, rec.rating);
  const tags = cuisineTags(rec.cuisine, rec.explanation);
  const isTop = rec.rank === 1;

  return (
    <article
      className={`group relative flex flex-col gap-space-md rounded-xl border bg-surface-container-low/80 p-space-md transition-all duration-300 ${
        isTop
          ? "border-primary-container/40 shadow-[0_0_40px_-10px_rgba(255,83,81,0.25),0_8px_30px_rgb(0,0,0,0.3)]"
          : "border-white/[0.07] shadow-[0_8px_30px_rgb(0,0,0,0.3)] hover:border-primary-container/40"
      }`}
    >
      <div className="flex flex-1 flex-col justify-between gap-space-xs">
        <div>
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-label-md font-bold shadow-md ${
                  isTop
                    ? "bg-gradient-to-r from-primary-container to-secondary text-white shadow-primary-container/40"
                    : "border border-white/[0.1] bg-surface-container-highest/90 text-primary-fixed-dim"
                }`}
              >
                {isTop ? (
                  <>
                    <span>#{rec.rank}</span>
                    <span className="text-[10px] font-normal opacity-90">
                      {match}% Match
                    </span>
                  </>
                ) : (
                  <span>
                    #{rec.rank} · {match}%
                  </span>
                )}
              </span>
              <h3 className="font-headline text-headline-sm text-on-surface transition-colors group-hover:text-primary">
                {rec.name}
              </h3>
            </div>
            <span className="text-on-surface-variant" aria-hidden>
              ⌞
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-label-sm text-on-surface-variant">
            <span className="font-medium text-on-surface">{rec.cuisine}</span>
            <span>•</span>
            <span className="font-semibold text-primary">
              {rec.rating.toFixed(1)} ★
            </span>
            <span>•</span>
            <span>{budgetDisplay(rec.estimated_cost)}</span>
          </div>
          <p className="mt-2.5 rounded-lg border border-white/[0.04] bg-surface-container-lowest/40 p-2.5 text-body-sm leading-relaxed text-on-surface-variant">
            <strong className="mr-1 text-label-sm font-semibold text-primary">
              Why it fits:
            </strong>
            {rec.explanation}
          </p>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {tags.map((tag, i) => (
            <span
              key={tag}
              className={`rounded-full px-2 py-0.5 text-label-sm ${
                i === tags.length - 1 && tags.length > 1
                  ? "bg-primary/10 text-primary"
                  : "bg-white/[0.04] text-on-surface-variant"
              }`}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}
