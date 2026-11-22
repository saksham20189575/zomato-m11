#!/usr/bin/env python3
"""Print cleaned corpus size, sample restaurants, and cost/rating notes."""

from __future__ import annotations

import statistics
from collections import Counter

from recommender.config import get_settings
from recommender.repository import RestaurantRepository


def main() -> None:
    settings = get_settings()
    repo = RestaurantRepository(settings=settings)
    restaurants = repo.load()

    print(f"Dataset: {settings.dataset_name}")
    print(f"Cache:   {settings.cache_dir / 'restaurants.parquet'}")
    print(f"Count:   {len(restaurants)} restaurants\n")

    print("Sample restaurants:")
    for restaurant in restaurants[:3]:
        print(
            f"  - [{restaurant.id}] {restaurant.name} | {restaurant.location} | "
            f"{restaurant.cuisine_display} | rating={restaurant.rating} | "
            f"cost={restaurant.cost} ({restaurant.cost_band})"
        )

    ratings = [r.rating for r in restaurants]
    costs = [r.cost for r in restaurants if r.cost is not None]
    bands = Counter(r.cost_band.value if r.cost_band else "none" for r in restaurants)

    print("\nDistributions (for Phase 2 threshold tuning):")
    print(
        f"  rating  mean={statistics.mean(ratings):.2f}  "
        f"median={statistics.median(ratings):.2f}  "
        f"min={min(ratings):.1f}  max={max(ratings):.1f}"
    )
    if costs:
        sorted_costs = sorted(costs)
        p33 = sorted_costs[int(0.33 * (len(sorted_costs) - 1))]
        p66 = sorted_costs[int(0.66 * (len(sorted_costs) - 1))]
        print(
            f"  cost    mean={statistics.mean(costs):.0f}  "
            f"median={statistics.median(costs):.0f}  "
            f"P33≈{p33:.0f}  P66≈{p66:.0f}"
        )
    print(f"  bands   {dict(bands)}")
    print("\nSee docs/data-dictionary.md for column mapping and band policy.")


if __name__ == "__main__":
    main()
