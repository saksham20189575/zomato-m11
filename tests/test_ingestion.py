"""Unit tests for rating/cost/cuisine normalization and cache behavior."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from recommender.config import Settings
from recommender.ingestion import (
    DatasetLoader,
    assign_cost_band,
    normalize_dataframe,
    parse_cost,
    parse_rating,
    split_cuisines,
)
from recommender.models import BudgetBand
from recommender.repository import RestaurantRepository

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "restaurants_raw.csv"


@pytest.fixture
def fixture_settings(tmp_path: Path) -> Settings:
    return Settings(
        DATASET_NAME=str(FIXTURE_CSV),
        CACHE_DIR=tmp_path,
        BUDGET_LOW_MAX=300,
        BUDGET_MEDIUM_MAX=550,
    )


def test_parse_rating_standard_and_noisy() -> None:
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating("3.8 /5") == 3.8
    assert parse_rating("NEW") is None
    assert parse_rating("-") is None
    assert parse_rating("") is None
    assert parse_rating(None) is None


def test_parse_cost_currency_and_commas() -> None:
    assert parse_cost("800") == 800.0
    assert parse_cost("1,200") == 1200.0
    assert parse_cost("₹550") == 550.0
    assert parse_cost("-") is None
    assert parse_cost(None) is None


def test_split_cuisines_delimiters() -> None:
    assert split_cuisines("North Indian, Mughlai, Chinese") == [
        "North Indian",
        "Mughlai",
        "Chinese",
    ]
    assert split_cuisines("Cafe / American | Continental") == [
        "Cafe",
        "American",
        "Continental",
    ]
    assert split_cuisines("") == []
    assert split_cuisines(None) == []


def test_assign_cost_band_boundaries() -> None:
    assert assign_cost_band(300, 300, 550) == BudgetBand.LOW
    assert assign_cost_band(301, 300, 550) == BudgetBand.MEDIUM
    assert assign_cost_band(550, 300, 550) == BudgetBand.MEDIUM
    assert assign_cost_band(551, 300, 550) == BudgetBand.HIGH
    assert assign_cost_band(None, 300, 550) is None


def test_normalize_dataframe_drops_invalid_rows(fixture_settings: Settings) -> None:
    df = pd.read_csv(FIXTURE_CSV)
    restaurants, meta = normalize_dataframe(df, fixture_settings)

    names = {r.name for r in restaurants}
    assert "Jalsa" in names
    assert "Currency Cafe" in names
    # Dropped: NEW rating, '-', empty name, empty cuisines
    assert "New Place" not in names
    assert "Dash Spot" not in names
    assert "No Cuisine Spot" not in names
    assert "" not in names
    assert meta["kept_rows"] >= 10
    assert all(r.rating is not None for r in restaurants)
    assert all(r.cuisines for r in restaurants)


def test_normalize_appends_city_and_splits_cuisines(fixture_settings: Settings) -> None:
    df = pd.read_csv(FIXTURE_CSV)
    restaurants, _ = normalize_dataframe(df, fixture_settings)
    by_name = {r.name: r for r in restaurants}

    jalsa = by_name["Jalsa"]
    assert "Bangalore" in jalsa.location
    assert "Banashankari" in jalsa.location
    assert "Chinese" in jalsa.cuisines

    meghana = by_name["Meghana Foods"]
    assert "Bangalore" in meghana.location  # Bengaluru normalized via address match
    assert meghana.cost == 600.0
    assert meghana.cost_band in {BudgetBand.LOW, BudgetBand.MEDIUM, BudgetBand.HIGH}

    truffles = by_name["Truffles"]
    assert truffles.cost == 1200.0
    assert "American" in truffles.cuisines


def test_cache_hit_avoids_rebuild(
    fixture_settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = DatasetLoader(settings=fixture_settings, force_refresh=True)
    first = loader.load()
    assert (tmp_path / "restaurants.parquet").exists()
    assert len(first) > 0

    def _boom() -> tuple[list, dict]:
        raise AssertionError("source should not be consulted on cache hit")

    loader.force_refresh = False
    monkeypatch.setattr(loader, "_load_from_source", _boom)
    second = loader.load()
    assert len(second) == len(first)
    assert {r.id for r in second} == {r.id for r in first}


def test_repository_load_and_all(fixture_settings: Settings) -> None:
    repo = RestaurantRepository(
        loader=DatasetLoader(settings=fixture_settings, force_refresh=True),
        settings=fixture_settings,
    )
    loaded = repo.load()
    assert len(loaded) == len(repo.all())
    assert len(repo) > 0
    sample = loaded[0]
    assert repo.get(sample.id) == sample
    assert repo.get("missing-id") is None
