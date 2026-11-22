"use client";

import { useCallback, useEffect, useState } from "react";
import {
  DEMO_EXTRAS,
  defaultLocation,
  fetchMeta,
  pickDemoLocation,
  postRecommend,
} from "@/lib/api";
import type { MetaResponse, ServiceResult, UiView } from "@/lib/types";
import {
  PreferencesPanel,
  type PrefsState,
} from "./PreferencesPanel";
import { ResultsPanel } from "./ResultsPanel";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";

const ANY = "Any cuisine";

function initialPrefs(meta: MetaResponse | null): PrefsState {
  return {
    location: meta ? defaultLocation(meta.locations) : "",
    cuisine: ANY,
    budget: "medium",
    minRating: 4.0,
    topK: meta?.default_top_k ?? 5,
    extras: "",
    mock: false,
  };
}

export function TasteRankApp() {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [prefs, setPrefs] = useState<PrefsState>(initialPrefs(null));
  const [view, setView] = useState<UiView>("idle");
  const [outcome, setOutcome] = useState<ServiceResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchMeta();
        if (cancelled) return;
        setMeta(data);
        setPrefs(initialPrefs(data));
        setMetaError(null);
      } catch (err) {
        if (cancelled) return;
        setMetaError(
          err instanceof Error ? err.message : "Failed to load meta from API",
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const patchPrefs = useCallback((patch: Partial<PrefsState>) => {
    setPrefs((prev) => ({ ...prev, ...patch }));
  }, []);

  const runRecommend = useCallback(
    async (override?: Partial<PrefsState>) => {
      const next = { ...prefs, ...override };
      if (!next.location) return;

      setView("loading");
      setOutcome(null);

      try {
        const result = await postRecommend({
          location: next.location,
          budget: next.budget,
          cuisine: next.cuisine === ANY ? null : next.cuisine,
          min_rating: next.minRating,
          additional_preferences: next.extras.trim() || null,
          top_k: next.topK,
          mock: next.mock,
        });
        setOutcome(result);
        if (result.status === "success") {
          setView("live");
        } else if (result.status === "empty") {
          setView("empty");
        } else {
          setView("error");
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unexpected recommendation error";
        setOutcome({
          status: "error",
          preferences: null,
          shortlist_size: 0,
          result: null,
          empty_reason_code: null,
          message,
          model_name: null,
        });
        setView("error");
      }
    },
    [prefs],
  );

  const onDemo = useCallback(() => {
    if (!meta) return;
    const demo: PrefsState = {
      location: pickDemoLocation(meta.locations),
      cuisine: meta.cuisines.includes("North Indian") ? "North Indian" : ANY,
      budget: "medium",
      minRating: 4.2,
      topK: meta.default_top_k,
      extras: DEMO_EXTRAS,
      mock: prefs.mock || !meta.has_llm_key,
    };
    setPrefs(demo);
    void runRecommend(demo);
  }, [meta, prefs.mock, runRecommend]);

  const onReset = useCallback(() => {
    setPrefs(initialPrefs(meta));
    setView("idle");
    setOutcome(null);
  }, [meta]);

  const onRelax = useCallback(() => {
    patchPrefs({ minRating: Math.max(0, prefs.minRating - 0.5), cuisine: ANY });
    setView("idle");
  }, [patchPrefs, prefs.minRating]);

  const systemReady = Boolean(meta) && !metaError;

  return (
    <div className="relative min-h-screen bg-surface font-body text-body-md text-on-surface">
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="absolute -top-[20%] left-1/2 h-[500px] w-[700px] -translate-x-1/2 rounded-full bg-primary-container/10 blur-[130px]" />
        <div className="absolute -bottom-[20%] -right-[10%] h-[500px] w-[600px] rounded-full bg-tertiary-container/10 blur-[140px]" />
      </div>

      <SiteHeader
        budget={prefs.budget}
        minRating={prefs.minRating}
        systemReady={systemReady}
      />

      <main className="relative z-10 flex min-h-[calc(100vh-80px)] w-full flex-col bg-transparent pt-20">
        <div className="mx-auto flex w-full max-w-content flex-col gap-space-xl px-margin py-space-lg md:px-margin-tablet lg:px-space-md">
          <header className="relative flex flex-col justify-between gap-space-lg md:flex-row md:items-end">
            <div className="flex max-w-2xl flex-col gap-space-xs">
              <div className="flex items-center gap-space-xs text-section-eyebrow uppercase tracking-widest text-primary">
                <span className="h-1.5 w-1.5 animate-tr-pulse rounded-full bg-primary-container" />
                <span>Culinary Intelligence · Bangalore Node</span>
              </div>
              <h1 className="font-display text-display-mobile leading-tight tracking-tight text-on-surface md:text-display">
                Taste
                <span className="bg-gradient-to-r from-primary-container to-secondary bg-clip-text text-transparent">
                  Rank
                </span>
              </h1>
              <p className="text-body-lg leading-relaxed text-on-surface-variant">
                AI picks that match your taste, budget, and neighborhood.
                Grounded in local gastronomy and real-time palate signals.
              </p>
              {metaError && (
                <p className="mt-2 rounded-lg border border-error/30 bg-error-container/20 px-3 py-2 text-body-sm text-error">
                  API unreachable: {metaError}. Start FastAPI on port 8000.
                </p>
              )}
            </div>
          </header>

          <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
            <PreferencesPanel
              prefs={prefs}
              locations={meta?.locations ?? []}
              cuisines={meta?.cuisines ?? []}
              loading={view === "loading"}
              onChange={patchPrefs}
              onSubmit={() => void runRecommend()}
              onDemo={onDemo}
              onReset={onReset}
            />
            <ResultsPanel
              view={view}
              outcome={outcome}
              location={prefs.location}
              onRetry={() => void runRecommend()}
              onRelax={onRelax}
            />
          </div>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
