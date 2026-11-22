"""CLI formatting and preference parsing tests (no network)."""

from __future__ import annotations

from recommender.filters import EmptyReasonCode
from recommender.models import (
    BudgetBand,
    Recommendation,
    RecommendationResult,
    RecommendationSource,
    UserPreferences,
)
from recommender.service import ServiceResult, ServiceStatus

from app.main import build_parser, format_results, preferences_from_args


def test_preferences_from_complete_flags() -> None:
    args = build_parser().parse_args(
        [
            "--location",
            "Bangalore",
            "--budget",
            "medium",
            "--cuisine",
            "Chinese",
            "--min-rating",
            "4.0",
            "--top-k",
            "3",
            "--extras",
            "family-friendly",
        ]
    )
    prefs = preferences_from_args(args)
    assert prefs is not None
    assert prefs.location == "Bangalore"
    assert prefs.budget == BudgetBand.MEDIUM
    assert prefs.additional_preferences == "family-friendly"
    assert prefs.top_k == 3


def test_preferences_from_incomplete_flags() -> None:
    args = build_parser().parse_args(["--location", "Bangalore"])
    assert preferences_from_args(args) is None


def test_preferences_cuisine_optional() -> None:
    args = build_parser().parse_args(
        [
            "--location",
            "Bangalore",
            "--budget",
            "medium",
            "--min-rating",
            "4.0",
        ]
    )
    prefs = preferences_from_args(args)
    assert prefs is not None
    assert prefs.cuisine is None


def test_format_empty_result() -> None:
    text = format_results(
        ServiceResult(
            status=ServiceStatus.EMPTY,
            preferences=UserPreferences(
                location="Delhi",
                budget=BudgetBand.LOW,
                cuisine="French",
                min_rating=4.9,
            ),
            empty_reason_code=EmptyReasonCode.NO_LOCATION_MATCH,
            message="No restaurants matched that location.",
        )
    )
    assert "No matching restaurants" in text
    assert "No restaurants matched that location" in text
    assert "broaden" in text.lower()


def test_format_success_includes_explanations() -> None:
    text = format_results(
        ServiceResult(
            status=ServiceStatus.SUCCESS,
            preferences=UserPreferences(
                location="Bangalore",
                budget=BudgetBand.MEDIUM,
                cuisine="Chinese",
                min_rating=4.0,
            ),
            shortlist_size=5,
            model_name="openai/gpt-oss-20b",
            result=RecommendationResult(
                summary="Top Chinese picks.",
                source=RecommendationSource.LLM,
                recommendations=[
                    Recommendation(
                        restaurant_id="id-a",
                        name="Alpha",
                        rank=1,
                        cuisine="Chinese",
                        rating=4.5,
                        estimated_cost=500,
                        explanation="Strong Chinese match with high rating.",
                    )
                ],
            ),
        )
    )
    assert "Alpha" in text
    assert "Strong Chinese match" in text
    assert "Groq LLM" in text
    assert "Top Chinese picks" in text


def test_format_mock_source_label() -> None:
    text = format_results(
        ServiceResult(
            status=ServiceStatus.SUCCESS,
            preferences=UserPreferences(
                location="Bangalore",
                budget=BudgetBand.MEDIUM,
                cuisine="Chinese",
                min_rating=4.0,
            ),
            shortlist_size=1,
            model_name="mock",
            result=RecommendationResult(
                source=RecommendationSource.LLM,
                recommendations=[
                    Recommendation(
                        restaurant_id="id-a",
                        name="Alpha",
                        rank=1,
                        cuisine="Chinese",
                        rating=4.5,
                        estimated_cost=500,
                        explanation="Mock explanation.",
                    )
                ],
            ),
        )
    )
    assert "Mock LLM" in text
    assert "Groq LLM" not in text
