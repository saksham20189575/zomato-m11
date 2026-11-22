#!/usr/bin/env python3
"""Manual Phase 3 check: rank a shortlist via mock or live Groq."""

from __future__ import annotations

import argparse
import json

from recommender.config import get_settings
from recommender.engine import RecommendationEngine
from recommender.filters import CandidateFilter
from recommender.llm_client import GroqLLMClient, MockLLMClient
from recommender.models import BudgetBand, UserPreferences
from recommender.repository import RestaurantRepository


def _mock_payload(candidate_ids: list[str]) -> str:
    recs = [
        {
            "restaurant_id": rid,
            "rank": i,
            "explanation": "Mock explanation: matched your filters.",
        }
        for i, rid in enumerate(candidate_ids[:3], start=1)
    ]
    return json.dumps(
        {
            "summary": "Mock ranking for offline Phase 3 preview.",
            "recommendations": recs,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Groq (requires LLM_API_KEY / GROQ_API_KEY)",
    )
    args = parser.parse_args()

    settings = get_settings()
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.MEDIUM,
        cuisine="Chinese",
        min_rating=4.0,
        additional_preferences="family-friendly",
        top_k=3,
    )

    restaurants = RestaurantRepository(settings=settings).load()
    filtered = CandidateFilter(settings=settings).filter(restaurants, prefs)
    if filtered.is_empty:
        print(f"Empty shortlist ({filtered.reason_code}): {filtered.message}")
        return

    candidates = filtered.restaurants
    if args.live:
        print(f"Live Groq model={settings.llm_model} base={settings.llm_base_url}")
        llm = GroqLLMClient(settings=settings)
    else:
        print("Mock LLM (pass --live for Groq)")
        llm = MockLLMClient(_mock_payload([r.id for r in candidates]))

    result = RecommendationEngine(llm, settings=settings).recommend(
        prefs, candidates
    )

    print(f"\nSource: {result.source.value}")
    if result.note:
        print(f"Note: {result.note}")
    if result.summary:
        print(f"Summary: {result.summary}")
    print(f"Recommendations ({len(result.recommendations)}):")
    for rec in result.recommendations:
        print(
            f"  {rec.rank}. [{rec.restaurant_id}] {rec.name} | {rec.cuisine} | "
            f"rating={rec.rating} cost={rec.estimated_cost}"
        )
        print(f"     {rec.explanation}")


if __name__ == "__main__":
    main()
