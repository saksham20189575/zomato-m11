"""Unit tests for RecommendationService orchestration (mocked LLM)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from recommender.config import Settings
from recommender.engine import RecommendationEngine
from recommender.filters import CandidateFilter, EmptyReasonCode
from recommender.llm_client import MockLLMClient
from recommender.models import (
    BudgetBand,
    RecommendationSource,
    Restaurant,
    UserPreferences,
)
from recommender.service import RecommendationService, ServiceStatus


class _FixedRepository:
    def __init__(self, restaurants: list[Restaurant], *, fail: bool = False) -> None:
        self._restaurants = restaurants
        self.fail = fail

    def load(self) -> list[Restaurant]:
        if self.fail:
            raise RuntimeError("disk exploded")
        return list(self._restaurants)


def _r(
    id: str,
    *,
    name: str = "R",
    location: str = "Koramangala, Bangalore",
    cuisines: list[str] | None = None,
    cost: float = 400.0,
    cost_band: BudgetBand = BudgetBand.MEDIUM,
    rating: float = 4.2,
    votes: int = 100,
) -> Restaurant:
    return Restaurant(
        id=id,
        name=name,
        location=location,
        cuisines=cuisines or ["Chinese"],
        cost=cost,
        cost_band=cost_band,
        rating=rating,
        votes=votes,
    )


@pytest.fixture
def corpus() -> list[Restaurant]:
    return [
        _r("id-a", name="Alpha", rating=4.5, votes=200),
        _r("id-b", name="Beta", rating=4.1, votes=80, cuisines=["Italian"]),
        _r(
            "id-mumbai",
            name="Bombay",
            location="Bandra, Mumbai",
            rating=4.4,
        ),
    ]


@pytest.fixture
def settings() -> Settings:
    return Settings(default_top_k=2, max_candidates=20, llm_model="mock-model")


def _service(
    corpus: list[Restaurant],
    settings: Settings,
    llm_payload: dict[str, Any] | None = None,
    *,
    fail_llm: bool = False,
    fail_load: bool = False,
) -> RecommendationService:
    if llm_payload is None:
        llm_payload = {
            "summary": "Great picks.",
            "recommendations": [
                {
                    "restaurant_id": "id-a",
                    "explanation": "Best Chinese match.",
                },
            ],
        }
    client = MockLLMClient(json.dumps(llm_payload), fail=fail_llm)
    return RecommendationService(
        repository=_FixedRepository(corpus, fail=fail_load),  # type: ignore[arg-type]
        candidate_filter=CandidateFilter(settings=settings),
        engine=RecommendationEngine(client, settings=settings),
        settings=settings,
    )


def _prefs(**overrides: object) -> UserPreferences:
    data: dict[str, Any] = {
        "location": "Bangalore",
        "budget": BudgetBand.MEDIUM,
        "cuisine": "Chinese",
        "min_rating": 4.0,
        "top_k": 2,
    }
    data.update(overrides)
    return UserPreferences(**data)


def test_happy_path_calls_llm_once(
    corpus: list[Restaurant], settings: Settings
) -> None:
    service = _service(corpus, settings)
    outcome = service.recommend(_prefs())
    assert outcome.status == ServiceStatus.SUCCESS
    assert outcome.shortlist_size == 1  # only Alpha is Chinese in Bangalore
    assert outcome.result is not None
    assert outcome.result.source == RecommendationSource.LLM
    assert outcome.result.recommendations[0].name == "Alpha"
    assert outcome.result.recommendations[0].explanation == "Best Chinese match."
    assert outcome.model_name == "mock-model"
    engine_client = service.engine.llm_client
    assert isinstance(engine_client, MockLLMClient)
    assert len(engine_client.calls) == 1


def test_empty_shortlist_skips_llm(
    corpus: list[Restaurant], settings: Settings
) -> None:
    service = _service(corpus, settings)
    outcome = service.recommend(_prefs(location="Delhi"))
    assert outcome.status == ServiceStatus.EMPTY
    assert outcome.empty_reason_code == EmptyReasonCode.NO_LOCATION_MATCH
    assert outcome.message
    assert outcome.result is None
    engine_client = service.engine.llm_client
    assert isinstance(engine_client, MockLLMClient)
    assert engine_client.calls == []


def test_llm_failure_uses_fallback(
    corpus: list[Restaurant], settings: Settings
) -> None:
    service = _service(corpus, settings, fail_llm=True)
    outcome = service.recommend(_prefs())
    assert outcome.status == ServiceStatus.SUCCESS
    assert outcome.result is not None
    assert outcome.result.source == RecommendationSource.FALLBACK
    assert outcome.result.note is not None
    assert "LLM" in outcome.result.note


def test_invalid_preferences_before_load(
    corpus: list[Restaurant], settings: Settings
) -> None:
    service = _service(corpus, settings)
    outcome = service.recommend(
        {"location": "", "budget": "medium", "cuisine": "Chinese", "min_rating": 4.0}
    )
    assert outcome.status == ServiceStatus.ERROR
    assert outcome.message is not None
    assert "Invalid preferences" in outcome.message


def test_repository_load_failure(
    corpus: list[Restaurant], settings: Settings
) -> None:
    service = _service(corpus, settings, fail_load=True)
    outcome = service.recommend(_prefs())
    assert outcome.status == ServiceStatus.ERROR
    assert "Could not load" in (outcome.message or "")
