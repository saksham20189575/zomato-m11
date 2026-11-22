#!/usr/bin/env python3
"""Manual Phase 2 check: print a Bangalore + cuisine + budget shortlist."""

from __future__ import annotations

from recommender.config import get_settings
from recommender.filters import CandidateFilter
from recommender.models import BudgetBand, UserPreferences
from recommender.repository import RestaurantRepository


def main() -> None:
    settings = get_settings()
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.MEDIUM,
        cuisine="Chinese",
        min_rating=4.0,
        additional_preferences="family-friendly",
        top_k=5,
    )

    restaurants = RestaurantRepository(settings=settings).load()
    result = CandidateFilter(settings=settings).filter(restaurants, prefs)

    print("Preferences:")
    print(
        f"  location={prefs.location!r}  budget={prefs.budget.value}  "
        f"cuisine={prefs.cuisine!r}  min_rating={prefs.min_rating}"
    )
    print(f"  max_candidates={settings.max_candidates}")
    print(f"Corpus size: {len(restaurants)}")

    if result.is_empty:
        print(f"\nEmpty shortlist ({result.reason_code}): {result.message}")
        return

    print(f"\nShortlist ({len(result.restaurants)}):")
    for i, r in enumerate(result.restaurants, start=1):
        print(
            f"  {i}. [{r.id}] {r.name} | {r.location} | {r.cuisine_display} | "
            f"rating={r.rating} votes={r.votes} | cost={r.cost} ({r.cost_band})"
        )


if __name__ == "__main__":
    main()
