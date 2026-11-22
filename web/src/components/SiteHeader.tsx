"use client";

import Link from "next/link";
import type { BudgetBand } from "@/lib/types";

const BUDGET_SHORT: Record<BudgetBand, string> = {
  low: "Low Budget",
  medium: "Medium Budget",
  high: "High Budget",
};

export function SiteHeader({
  budget,
  minRating,
  systemReady,
}: {
  budget: BudgetBand;
  minRating: number;
  systemReady: boolean;
}) {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06] bg-surface-container-lowest/80 backdrop-blur-xl">
      <div className="mx-auto flex h-20 w-full max-w-shell items-center justify-between gap-gutter px-margin md:px-margin-tablet lg:px-margin-desktop">
        <div className="flex items-center gap-space-lg">
          <Link className="group flex items-center gap-space-sm" href="/">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary-container to-secondary text-sm font-bold text-white shadow-[0_0_20px_-4px_rgba(255,83,81,0.5)]">
              T
            </span>
            <span className="font-headline text-headline-sm tracking-tight text-on-surface">
              Taste<span className="text-primary">Rank</span>
            </span>
          </Link>
          <nav className="hidden items-center gap-space-xs rounded-full border border-white/[0.05] bg-surface-container-low/60 p-1.5 lg:flex">
            <span className="rounded-full bg-primary-container px-space-md py-space-xs text-label-lg text-on-primary-container shadow-[0_0_24px_-4px_rgba(255,83,81,0.4)]">
              Recommend
            </span>
            <span className="rounded-full px-space-md py-space-xs text-label-lg text-on-surface-variant">
              Explore Bangalore
            </span>
            <span className="rounded-full px-space-md py-space-xs text-label-lg text-on-surface-variant">
              Saved Tastes
            </span>
            <span className="rounded-full px-space-md py-space-xs text-label-lg text-on-surface-variant">
              API Docs
            </span>
          </nav>
        </div>
        <div className="flex items-center gap-space-sm">
          <div className="hidden items-center gap-1.5 rounded-full border border-white/[0.06] bg-surface-container/70 px-3 py-1 text-label-md text-on-surface-variant sm:flex">
            <span className="text-[14px] text-primary">📍</span>
            <span>Bangalore, IN</span>
          </div>
          <div className="hidden items-center gap-1.5 rounded-full border border-white/[0.04] bg-surface-container/50 px-3 py-1 text-label-sm text-on-surface-variant xl:flex">
            <span>
              {BUDGET_SHORT[budget]} • Min {minRating.toFixed(1)}★
            </span>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-white/[0.06] bg-surface-container-high/60 px-3 py-1 text-label-sm text-on-surface md:flex">
            <span
              className={`h-1.5 w-1.5 rounded-full ${systemReady ? "animate-tr-pulse bg-primary-container" : "bg-outline"}`}
            />
            <span className="text-on-surface-variant">System:</span>
            <span className={`font-medium ${systemReady ? "text-primary" : "text-outline"}`}>
              {systemReady ? "Ready" : "Offline"}
            </span>
          </div>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-[13px] font-semibold text-on-primary">
            ★
          </div>
        </div>
      </div>
    </header>
  );
}
