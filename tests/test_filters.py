"""Unit tests for CandidateFilter combinations and empty shortlist paths."""

from __future__ import annotations

import pytest

from recommender.filters import (
    CandidateFilter,
    EmptyReasonCode,
    matches_cuisine,
    matches_location,
)
from recommender.models import BudgetBand, Restaurant, UserPreferences


def _r(
    id: str,
    *,
    name: str = "R",
    location: str = "Koramangala 5th Block, Bangalore",
    cuisines: list[str] | None = None,
    cost: float = 400.0,
    cost_band: BudgetBand | None = BudgetBand.MEDIUM,
    rating: float = 4.0,
    votes: int = 100,
) -> Restaurant:
    return Restaurant(
        id=id,
        name=name,
        location=location,
        cuisines=cuisines or ["North Indian", "Chinese"],
        cost=cost,
        cost_band=cost_band,
        rating=rating,
        votes=votes,
    )


@pytest.fixture
def corpus() -> list[Restaurant]:
    return [
        _r("id-jalsa", name="Jalsa", location="Banashankari, Bangalore",
           cuisines=["North Indian", "Mughlai", "Chinese"], cost=800,
           cost_band=BudgetBand.HIGH, rating=4.1, votes=775),
        _r("id-truffles", name="Truffles", location="Indiranagar, Bangalore",
           cuisines=["Cafe", "American", "Continental"], cost=1200,
           cost_band=BudgetBand.HIGH, rating=4.4, votes=4500),
        _r("id-meghana", name="Meghana Foods",
           location="Koramangala 5th Block, Bangalore",
           cuisines=["Andhra", "Biryani"], cost=600,
           cost_band=BudgetBand.HIGH, rating=4.2, votes=3000),
        _r("id-empire", name="Empire", location="BTM, Bangalore",
           cuisines=["North Indian", "Mughlai"], cost=500,
           cost_band=BudgetBand.MEDIUM, rating=4.0, votes=2000),
        _r("id-ctr", name="CTR", location="Jayanagar, Bangalore",
           cuisines=["South Indian"], cost=150,
           cost_band=BudgetBand.LOW, rating=4.7, votes=6000),
        _r("id-dominos", name="Dominos", location="JP Nagar, Bangalore",
           cuisines=["Pizza", "Fast Food"], cost=400,
           cost_band=BudgetBand.MEDIUM, rating=3.5, votes=400),
        _r("id-unknown-cost", name="Mystery", location="HSR, Bangalore",
           cuisines=["Italian"], cost=None, cost_band=None,
           rating=4.5, votes=50),
        _r("id-mumbai", name="Bombay Cafe", location="Bandra, Mumbai",
           cuisines=["Cafe", "Italian"], cost=500,
           cost_band=BudgetBand.MEDIUM, rating=4.3, votes=800),
    ]


def test_matches_location_case_and_short_query() -> None:
    assert matches_location("Banashankari, Bangalore", "bangalore")
    assert matches_location("Banashankari, Bangalore", " Banashankari ")
    assert not matches_location("Banashankari, Bangalore", "Mumbai")
    # Ultra-short: token match only (CF-02)
    assert matches_location("BTM, Bangalore", "btm")
    assert not matches_location("Albania Street, Bangalore", "Al")


def test_matches_cuisine_token_boundaries() -> None:
    assert matches_cuisine(["North Indian", "Chinese"], "Indian")
    assert matches_cuisine(["North Indian", "Chinese"], "chinese")
    assert matches_cuisine(["Cafe", "American"], "Cafe, Mexican")  # any-of
    assert not matches_cuisine(["Chinese"], "Chi")
    assert not matches_cuisine(["Italian"], "Chinese")


def test_happy_path_returns_expected_ids(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.HIGH,
        cuisine="North Indian",
        min_rating=4.0,
    )
    result = CandidateFilter(max_candidates=20).filter(corpus, prefs)
    ids = [r.id for r in result.restaurants]
    assert ids == ["id-jalsa"]  # only HIGH + North Indian + rating>=4 in Bangalore
    assert result.reason_code is None
    assert result.message is None


def test_rating_too_high_returns_empty(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.LOW,
        cuisine="South Indian",
        min_rating=4.9,
    )
    result = CandidateFilter(max_candidates=20).filter(corpus, prefs)
    assert result.is_empty
    assert result.reason_code == EmptyReasonCode.NO_RATING_MATCH
    assert result.message


def test_wrong_city_returns_empty(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Delhi",
        budget=BudgetBand.MEDIUM,
        cuisine="Cafe",
        min_rating=3.0,
    )
    result = CandidateFilter(max_candidates=20).filter(corpus, prefs)
    assert result.is_empty
    assert result.reason_code == EmptyReasonCode.NO_LOCATION_MATCH


def test_cuisine_mismatch_returns_empty(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.MEDIUM,
        cuisine="Japanese",
        min_rating=3.0,
    )
    result = CandidateFilter(max_candidates=20).filter(corpus, prefs)
    assert result.is_empty
    assert result.reason_code == EmptyReasonCode.NO_CUISINE_MATCH


def test_optional_cuisine_skips_cuisine_filter(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.MEDIUM,
        cuisine=None,
        min_rating=4.0,
    )
    result = CandidateFilter(max_candidates=20).filter(corpus, prefs)
    assert not result.is_empty
    assert all(r.cost_band == BudgetBand.MEDIUM for r in result.restaurants)
    assert all(r.rating >= 4.0 for r in result.restaurants)


def test_budget_excludes_null_cost_band(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="HSR",
        budget=BudgetBand.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )
    result = CandidateFilter(max_candidates=20).filter(corpus, prefs)
    assert result.is_empty
    assert result.reason_code == EmptyReasonCode.NO_BUDGET_MATCH


def test_truncation_respects_max_candidates(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.HIGH,
        cuisine="Chinese, Biryani, American",
        min_rating=3.0,
    )
    result = CandidateFilter(max_candidates=2).filter(corpus, prefs)
    assert len(result.restaurants) == 2
    # Soft rank: Truffles 4.4/4500, Meghana 4.2/3000, Jalsa 4.1/775
    assert [r.id for r in result.restaurants] == ["id-truffles", "id-meghana"]


def test_soft_rank_ties_use_id(corpus: list[Restaurant]) -> None:
    tied = [
        _r("id-b", name="B", rating=4.0, votes=10, cost_band=BudgetBand.LOW,
           cuisines=["South Indian"], location="Jayanagar, Bangalore"),
        _r("id-a", name="A", rating=4.0, votes=10, cost_band=BudgetBand.LOW,
           cuisines=["South Indian"], location="Jayanagar, Bangalore"),
    ]
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.LOW,
        cuisine="South Indian",
        min_rating=4.0,
    )
    result = CandidateFilter(max_candidates=10).filter(tied, prefs)
    assert [r.id for r in result.restaurants] == ["id-a", "id-b"]


def test_deterministic_for_same_inputs(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.MEDIUM,
        cuisine="North Indian",
        min_rating=3.5,
    )
    filt = CandidateFilter(max_candidates=10)
    a = [r.id for r in filt.filter(corpus, prefs).restaurants]
    b = [r.id for r in filt.filter(corpus, prefs).restaurants]
    assert a == b == ["id-empire"]


def test_cuisine_among_many_still_matches() -> None:
    restaurant = _r(
        "multi",
        cuisines=["North Indian", "Mughlai", "Chinese"],
        cost_band=BudgetBand.HIGH,
        location="Banashankari, Bangalore",
    )
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.HIGH,
        cuisine="Chinese",
        min_rating=3.0,
    )
    result = CandidateFilter(max_candidates=5).filter([restaurant], prefs)
    assert [r.id for r in result.restaurants] == ["multi"]


def test_relaxation_flag_not_implemented(corpus: list[Restaurant]) -> None:
    prefs = UserPreferences(
        location="Bangalore",
        budget=BudgetBand.LOW,
        cuisine="South Indian",
        min_rating=4.0,
    )
    with pytest.raises(NotImplementedError):
        CandidateFilter(max_candidates=5, enable_relaxation=True).filter(corpus, prefs)
