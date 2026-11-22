"""Unit tests for ResponseParser grounding and fallback."""

from __future__ import annotations

import json

import pytest

from recommender.models import BudgetBand, RecommendationSource, Restaurant
from recommender.parser import ParseError, ResponseParser, build_fallback_result


def _r(
    id: str,
    *,
    name: str = "R",
    cuisines: list[str] | None = None,
    cost: float | None = 400.0,
    rating: float = 4.0,
    votes: int = 100,
) -> Restaurant:
    return Restaurant(
        id=id,
        name=name,
        location="Koramangala, Bangalore",
        cuisines=cuisines or ["North Indian"],
        cost=cost,
        cost_band=BudgetBand.MEDIUM,
        rating=rating,
        votes=votes,
    )


@pytest.fixture
def candidates() -> list[Restaurant]:
    return [
        _r("id-a", name="Alpha", cuisines=["Chinese"], rating=4.5, votes=200, cost=500),
        _r("id-b", name="Beta", cuisines=["Italian"], rating=4.1, votes=80, cost=450),
        _r("id-c", name="Gamma", cuisines=["Cafe"], rating=3.9, votes=50, cost=300),
    ]


@pytest.fixture
def parser() -> ResponseParser:
    return ResponseParser()


def test_valid_json_parses(parser: ResponseParser, candidates: list[Restaurant]) -> None:
    payload = {
        "summary": "Great Chinese options.",
        "recommendations": [
            {
                "restaurant_id": "id-a",
                "name": "Wrong Name From LLM",
                "rank": 1,
                "cuisine": "fake",
                "rating": 9.9,
                "estimated_cost": 1,
                "explanation": "Strong Chinese match with high rating.",
            },
            {
                "restaurant_id": "id-b",
                "rank": 2,
                "explanation": "Solid Italian backup in budget.",
            },
        ],
    }
    result = parser.parse(json.dumps(payload), candidates, top_k=5)
    assert result.source == RecommendationSource.LLM
    assert result.summary == "Great Chinese options."
    assert [r.restaurant_id for r in result.recommendations] == ["id-a", "id-b"]
    # Dataset fields win over LLM copies
    assert result.recommendations[0].name == "Alpha"
    assert result.recommendations[0].rating == 4.5
    assert result.recommendations[0].cuisine == "Chinese"
    assert result.recommendations[0].estimated_cost == 500


def test_hallucinated_id_dropped(
    parser: ResponseParser, candidates: list[Restaurant]
) -> None:
    payload = {
        "recommendations": [
            {
                "restaurant_id": "not-in-shortlist",
                "explanation": "Invented place",
            },
            {
                "restaurant_id": "id-b",
                "explanation": "Real candidate",
            },
        ]
    }
    result = parser.parse(json.dumps(payload), candidates, top_k=5)
    assert [r.restaurant_id for r in result.recommendations] == ["id-b"]


def test_markdown_fenced_json_parses(
    parser: ResponseParser, candidates: list[Restaurant]
) -> None:
    inner = {
        "recommendations": [
            {"restaurant_id": "id-a", "explanation": "Top pick"},
        ]
    }
    fenced = f"Here you go:\n```json\n{json.dumps(inner)}\n```\n"
    result = parser.parse(fenced, candidates, top_k=3)
    assert len(result.recommendations) == 1
    assert result.recommendations[0].restaurant_id == "id-a"


def test_all_hallucinations_raise(
    parser: ResponseParser, candidates: list[Restaurant]
) -> None:
    payload = {
        "recommendations": [
            {"restaurant_id": "ghost-1", "explanation": "Nope"},
            {"restaurant_id": "ghost-2", "explanation": "Nope"},
        ]
    }
    with pytest.raises(ParseError, match="hallucinated|invalid"):
        parser.parse(json.dumps(payload), candidates, top_k=3)


def test_duplicate_ids_deduped(
    parser: ResponseParser, candidates: list[Restaurant]
) -> None:
    payload = {
        "recommendations": [
            {"restaurant_id": "id-a", "rank": 1, "explanation": "First"},
            {"restaurant_id": "id-a", "rank": 2, "explanation": "Dup"},
            {"restaurant_id": "id-c", "rank": 3, "explanation": "Third"},
        ]
    }
    result = parser.parse(json.dumps(payload), candidates, top_k=5)
    assert [r.restaurant_id for r in result.recommendations] == ["id-a", "id-c"]


def test_top_k_truncation(
    parser: ResponseParser, candidates: list[Restaurant]
) -> None:
    payload = {
        "recommendations": [
            {"restaurant_id": "id-a", "rank": 1, "explanation": "A"},
            {"restaurant_id": "id-b", "rank": 2, "explanation": "B"},
            {"restaurant_id": "id-c", "rank": 3, "explanation": "C"},
        ]
    }
    result = parser.parse(json.dumps(payload), candidates, top_k=2)
    assert len(result.recommendations) == 2
    assert [r.rank for r in result.recommendations] == [1, 2]


def test_fallback_ranks_by_rating(candidates: list[Restaurant]) -> None:
    result = build_fallback_result(candidates, top_k=2)
    assert result.source == RecommendationSource.FALLBACK
    assert [r.restaurant_id for r in result.recommendations] == ["id-a", "id-b"]
    assert "LLM unavailable" in result.recommendations[0].explanation
    assert result.note is not None
