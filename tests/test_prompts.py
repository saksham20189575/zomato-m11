"""Unit tests for PromptBuilder."""

from __future__ import annotations

import json

import pytest

from recommender.models import BudgetBand, Restaurant, UserPreferences
from recommender.prompts import PromptBuilder


@pytest.fixture
def prefs() -> UserPreferences:
    return UserPreferences(
        location="Bangalore",
        budget=BudgetBand.MEDIUM,
        cuisine="Chinese",
        min_rating=4.0,
        additional_preferences="family-friendly",
        top_k=3,
    )


@pytest.fixture
def candidates() -> list[Restaurant]:
    return [
        Restaurant(
            id='id-"special"',
            name='O\'Brien\'s Café & "Grill"',
            location="Koramangala, Bangalore",
            cuisines=["Chinese", "Asian"],
            cost=450.0,
            cost_band=BudgetBand.MEDIUM,
            rating=4.2,
            votes=120,
            raw={"huge": "should-not-appear" * 50},
        )
    ]


def test_prompt_includes_prefs_and_candidates(
    prefs: UserPreferences, candidates: list[Restaurant]
) -> None:
    payload = PromptBuilder().build(prefs, candidates, top_k=3)
    assert "ONLY from the provided candidate list" in payload.system
    assert "JSON only" in payload.system

    user = json.loads(payload.user)
    assert user["preferences"]["location"] == "Bangalore"
    assert user["preferences"]["additional_preferences"] == "family-friendly"
    assert user["preferences"]["top_k"] == 3
    assert user["candidates"][0]["restaurant_id"] == 'id-"special"'
    assert user["candidates"][0]["name"] == 'O\'Brien\'s Café & "Grill"'
    assert "raw" not in user["candidates"][0]
    assert "huge" not in payload.user


def test_omits_empty_extras(candidates: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.LOW,
        cuisine="South Indian",
        min_rating=3.5,
        additional_preferences=None,
    )
    payload = PromptBuilder().build(prefs, candidates, top_k=2)
    user = json.loads(payload.user)
    assert "additional_preferences" not in user["preferences"]


def test_empty_candidates_rejected(prefs: UserPreferences) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        PromptBuilder().build(prefs, [], top_k=3)


def test_as_messages(prefs: UserPreferences, candidates: list[Restaurant]) -> None:
    messages = PromptBuilder().build(prefs, candidates, top_k=1).as_messages()
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
