"""Unit tests for RecommendationEngine with mocked LLM (offline)."""

from __future__ import annotations

import json

from recommender.config import Settings
from recommender.engine import RecommendationEngine
from recommender.llm_client import MockLLMClient
from recommender.models import (
    BudgetBand,
    RecommendationSource,
    Restaurant,
    UserPreferences,
)


def _candidates() -> list[Restaurant]:
    return [
        Restaurant(
            id="id-a",
            name="Alpha",
            location="Bangalore",
            cuisines=["Chinese"],
            cost=500.0,
            cost_band=BudgetBand.MEDIUM,
            rating=4.5,
            votes=200,
        ),
        Restaurant(
            id="id-b",
            name="Beta",
            location="Bangalore",
            cuisines=["Italian"],
            cost=450.0,
            cost_band=BudgetBand.MEDIUM,
            rating=4.0,
            votes=80,
        ),
    ]


def _prefs(**overrides: object) -> UserPreferences:
    data: dict = {
        "location": "Bangalore",
        "budget": BudgetBand.MEDIUM,
        "cuisine": "Chinese",
        "min_rating": 4.0,
        "top_k": 2,
    }
    data.update(overrides)
    return UserPreferences(**data)


def test_engine_parses_valid_mock_response() -> None:
    payload = {
        "summary": "Chinese first.",
        "recommendations": [
            {
                "restaurant_id": "id-a",
                "explanation": "Best Chinese match.",
            },
            {
                "restaurant_id": "id-b",
                "explanation": "Italian backup.",
            },
        ],
    }
    engine = RecommendationEngine(
        MockLLMClient(json.dumps(payload)),
        settings=Settings(default_top_k=5),
    )
    result = engine.recommend(_prefs(), _candidates())
    assert result.source == RecommendationSource.LLM
    assert [r.restaurant_id for r in result.recommendations] == ["id-a", "id-b"]
    assert result.recommendations[0].explanation == "Best Chinese match."


def test_engine_falls_back_on_llm_failure() -> None:
    engine = RecommendationEngine(
        MockLLMClient("ignored", fail=True),
        settings=Settings(default_top_k=5),
    )
    result = engine.recommend(_prefs(), _candidates())
    assert result.source == RecommendationSource.FALLBACK
    assert [r.restaurant_id for r in result.recommendations] == ["id-a", "id-b"]
    assert result.note is not None
    assert "LLM" in result.note


def test_engine_falls_back_on_bad_json() -> None:
    engine = RecommendationEngine(
        MockLLMClient("not-json-at-all"),
        settings=Settings(default_top_k=5),
    )
    result = engine.recommend(_prefs(top_k=1), _candidates())
    assert result.source == RecommendationSource.FALLBACK
    assert len(result.recommendations) == 1
    assert result.recommendations[0].restaurant_id == "id-a"


def test_engine_falls_back_when_all_ids_hallucinated() -> None:
    payload = {
        "recommendations": [
            {"restaurant_id": "ghost", "explanation": "Nope"},
        ]
    }
    engine = RecommendationEngine(
        MockLLMClient(json.dumps(payload)),
        settings=Settings(default_top_k=5),
    )
    result = engine.recommend(_prefs(), _candidates())
    assert result.source == RecommendationSource.FALLBACK
