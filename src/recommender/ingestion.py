"""Dataset loading, normalization, and local cache."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

from recommender.config import Settings, get_settings
from recommender.models import BudgetBand, Restaurant

logger = logging.getLogger(__name__)

CACHE_FILENAME = "restaurants.parquet"

REQUIRED_SOURCE_COLUMNS = (
    "name",
    "location",
    "cuisines",
    "rate",
    "approx_cost(for two people)",
)

RAW_KEEP_COLUMNS = (
    "url",
    "address",
    "rest_type",
    "dish_liked",
    "online_order",
    "book_table",
    "listed_in(type)",
    "listed_in(city)",
    "votes",
)

_RATING_RE = re.compile(r"(\d+(?:\.\d+)?)")
_COST_RE = re.compile(r"(\d+(?:\.\d+)?)")
_CUISINE_SPLIT_RE = re.compile(r"[,/|]+")
_CITY_RE = re.compile(r"\b(bangalore|bengaluru)\b", re.IGNORECASE)


def parse_rating(value: Any) -> float | None:
    """Parse Zomato-style ratings (`4.1/5`, `3.8 /5`) into a 0–5 float.

    Non-numeric markers (`NEW`, `-`, blank) return None.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NEW", "-", "NAN", "NONE", "NULL"}:
        return None
    match = _RATING_RE.search(text)
    if not match:
        return None
    rating = float(match.group(1))
    # Values like "4.1/5" are already on a 0–5 scale.
    if rating > 5.0 and "/" in text:
        # Unexpected "8/10" style — normalize to 0–5 if denominator present.
        parts = text.replace(" ", "").split("/")
        try:
            return round(float(parts[0]) / float(parts[1]) * 5.0, 2)
        except (ValueError, ZeroDivisionError, IndexError):
            return None
    if rating < 0 or rating > 5:
        return None
    return rating


def parse_cost(value: Any) -> float | None:
    """Extract numeric approx cost for two from strings like `₹1,200` or `800`."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NAN", "NONE", "NULL", "-"}:
        return None
    cleaned = re.sub(r"[₹Rs\.]", "", text, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", "").strip()
    match = _COST_RE.search(cleaned)
    if not match:
        return None
    cost = float(match.group(1))
    if cost < 0:
        return None
    return cost


def split_cuisines(value: Any) -> list[str]:
    """Split multi-cuisine cells on comma / slash / pipe and trim tokens."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return []
    parts = _CUISINE_SPLIT_RE.split(text)
    return [part.strip() for part in parts if part.strip()]


def parse_votes(value: Any) -> int:
    """Coerce votes to int; missing / non-numeric → 0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    try:
        return max(0, int(float(text)))
    except ValueError:
        return 0


def _stable_id(
    name: str,
    location: str,
    address: str,
    *,
    url: str = "",
    listed_in_type: str = "",
) -> str:
    """Stable id; url / listing type distinguish duplicate Zomato rows (DI-18)."""
    payload = f"{name}|{location}|{address}|{url}|{listed_in_type}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:12]


def dedupe_restaurants(restaurants: list[Restaurant]) -> list[Restaurant]:
    """Keep one row per (name, location): highest rating, then votes, then id."""
    best: dict[tuple[str, str], Restaurant] = {}
    for restaurant in restaurants:
        key = (restaurant.name.casefold(), restaurant.location.casefold())
        current = best.get(key)
        if current is None:
            best[key] = restaurant
            continue
        challenger = (restaurant.rating, restaurant.votes, restaurant.id)
        incumbent = (current.rating, current.votes, current.id)
        if challenger > incumbent:
            best[key] = restaurant
    # Preserve deterministic order by id for stable downstream shortlists.
    return sorted(best.values(), key=lambda r: r.id)


def _normalize_location(locality: Any, address: Any) -> str | None:
    if locality is None or (isinstance(locality, float) and pd.isna(locality)):
        return None
    loc = str(locality).strip()
    if not loc or loc.lower() in {"nan", "none", "null"}:
        return None

    city: str | None = None
    if address is not None and not (isinstance(address, float) and pd.isna(address)):
        match = _CITY_RE.search(str(address))
        if match:
            # Canonical city spelling for search; keep Bangalore as primary label.
            raw_city = match.group(1).lower()
            city = "Bangalore" if raw_city in {"bangalore", "bengaluru"} else match.group(1)

    if city and city.lower() not in loc.lower():
        return f"{loc}, {city}"
    return loc


def assign_cost_band(
    cost: float | None,
    low_max: float,
    medium_max: float,
) -> BudgetBand | None:
    """Map numeric cost to low/medium/high using inclusive upper bounds."""
    if cost is None:
        return None
    if cost <= low_max:
        return BudgetBand.LOW
    if cost <= medium_max:
        return BudgetBand.MEDIUM
    return BudgetBand.HIGH


def _resolve_thresholds(
    costs: pd.Series,
    settings: Settings,
) -> tuple[float, float]:
    """Compute P33/P66 cutoffs; fall back to config if degenerate."""
    valid = costs.dropna()
    if valid.empty:
        return float(settings.budget_low_max), float(settings.budget_medium_max)

    low_max = float(valid.quantile(0.33))
    medium_max = float(valid.quantile(0.66))
    if medium_max <= low_max:
        logger.warning(
            "Degenerate cost percentiles (P33=%.2f, P66=%.2f); using config thresholds",
            low_max,
            medium_max,
        )
        return float(settings.budget_low_max), float(settings.budget_medium_max)
    return low_max, medium_max


def normalize_dataframe(
    df: pd.DataFrame,
    settings: Settings | None = None,
) -> tuple[list[Restaurant], dict[str, float]]:
    """Normalize a raw Zomato DataFrame into Restaurant records + band thresholds."""
    settings = settings or get_settings()
    missing = [col for col in REQUIRED_SOURCE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset missing required columns: {missing}. "
            f"Present columns: {list(df.columns)}"
        )
    if df.empty:
        raise ValueError("Dataset has zero rows after load")

    parsed_costs = df["approx_cost(for two people)"].map(parse_cost)
    low_max, medium_max = _resolve_thresholds(parsed_costs, settings)

    restaurants: list[Restaurant] = []
    for _, row in df.iterrows():
        name = row.get("name")
        if name is None or (isinstance(name, float) and pd.isna(name)):
            continue
        name_str = str(name).strip()
        if not name_str:
            continue

        location = _normalize_location(row.get("location"), row.get("address"))
        if not location:
            continue

        rating = parse_rating(row.get("rate"))
        if rating is None:
            continue

        cuisines = split_cuisines(row.get("cuisines"))
        if not cuisines:
            continue

        cost = parse_cost(row.get("approx_cost(for two people)"))
        cost_band = assign_cost_band(cost, low_max, medium_max)
        votes = parse_votes(row.get("votes"))
        address = row.get("address")
        address_str = (
            ""
            if address is None or (isinstance(address, float) and pd.isna(address))
            else str(address)
        )

        raw: dict[str, Any] = {}
        for col in RAW_KEEP_COLUMNS:
            if col not in df.columns:
                continue
            value = row.get(col)
            if value is None or (isinstance(value, float) and pd.isna(value)):
                continue
            raw[col] = value.item() if hasattr(value, "item") else value

        url_val = raw.get("url", "")
        url_str = "" if url_val is None else str(url_val)
        listed_in = raw.get("listed_in(type)", "")
        listed_in_str = "" if listed_in is None else str(listed_in)

        restaurants.append(
            Restaurant(
                id=_stable_id(
                    name_str,
                    location,
                    address_str,
                    url=url_str,
                    listed_in_type=listed_in_str,
                ),
                name=name_str,
                location=location,
                cuisines=cuisines,
                cost=cost,
                cost_band=cost_band,
                rating=rating,
                votes=votes,
                raw=raw,
            )
        )

    if not restaurants:
        raise ValueError("No valid restaurants after normalization")

    before_dedupe = len(restaurants)
    restaurants = dedupe_restaurants(restaurants)

    meta = {
        "budget_low_max": low_max,
        "budget_medium_max": medium_max,
        "source_rows": float(len(df)),
        "kept_rows": float(len(restaurants)),
        "pre_dedupe_rows": float(before_dedupe),
    }
    return restaurants, meta


def restaurants_to_frame(restaurants: list[Restaurant]) -> pd.DataFrame:
    """Serialize Restaurant models for parquet/CSV cache."""
    rows = []
    for r in restaurants:
        rows.append(
            {
                "id": r.id,
                "name": r.name,
                "location": r.location,
                "cuisines": "|".join(r.cuisines),
                "cost": r.cost,
                "cost_band": r.cost_band.value if r.cost_band else None,
                "rating": r.rating,
                "votes": r.votes,
                "raw_json": json.dumps(r.raw, ensure_ascii=False, default=str),
            }
        )
    return pd.DataFrame(rows)


def frame_to_restaurants(df: pd.DataFrame) -> list[Restaurant]:
    """Deserialize cached frame back into Restaurant models."""
    required = {"id", "name", "location", "cuisines", "rating"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Corrupt cache: missing columns {sorted(missing)}")

    restaurants: list[Restaurant] = []
    for _, row in df.iterrows():
        cuisines_val = row["cuisines"]
        if isinstance(cuisines_val, list):
            cuisines = [str(c).strip() for c in cuisines_val if str(c).strip()]
        else:
            cuisines = split_cuisines(cuisines_val)

        band_raw = row.get("cost_band")
        cost_band = None
        if band_raw is not None and not (isinstance(band_raw, float) and pd.isna(band_raw)):
            cost_band = BudgetBand(str(band_raw).strip().lower())

        cost_val = row.get("cost")
        cost = None if cost_val is None or (isinstance(cost_val, float) and pd.isna(cost_val)) else float(cost_val)

        raw: dict[str, Any] = {}
        raw_json = row.get("raw_json")
        if raw_json is not None and not (isinstance(raw_json, float) and pd.isna(raw_json)):
            try:
                parsed = json.loads(str(raw_json))
                if isinstance(parsed, dict):
                    raw = parsed
            except json.JSONDecodeError:
                raw = {}
        else:
            legacy_raw = row.get("raw")
            if isinstance(legacy_raw, dict):
                raw = legacy_raw

        restaurants.append(
            Restaurant(
                id=str(row["id"]),
                name=str(row["name"]),
                location=str(row["location"]),
                cuisines=cuisines,
                cost=cost,
                cost_band=cost_band,
                rating=float(row["rating"]),
                votes=parse_votes(row.get("votes")),
                raw=raw,
            )
        )
    return restaurants


class DatasetLoader:
    """Fetch / cache the Hugging Face Zomato dataset and normalize rows."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        cache_path: Path | None = None,
        force_refresh: bool = False,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache_dir = Path(self.settings.cache_dir)
        self.cache_path = cache_path or (self.cache_dir / CACHE_FILENAME)
        self.force_refresh = force_refresh
        self.last_meta: dict[str, float] = {}

    def load(self) -> list[Restaurant]:
        """Return cleaned restaurants, preferring local cache when present."""
        if not self.force_refresh and self.cache_path.exists():
            try:
                restaurants = self._load_cache()
                logger.info(
                    "Loaded %s restaurants from cache %s",
                    len(restaurants),
                    self.cache_path,
                )
                return restaurants
            except Exception as exc:  # noqa: BLE001 — rebuild on any cache failure
                logger.warning(
                    "Cache unreadable (%s); rebuilding from source",
                    exc,
                )

        restaurants, meta = self._load_from_source()
        self.last_meta = meta
        self._write_cache(restaurants)
        return restaurants

    def _load_cache(self) -> list[Restaurant]:
        df = pd.read_parquet(self.cache_path)
        restaurants = frame_to_restaurants(df)
        if not restaurants:
            raise ValueError("Cache contained zero restaurants")
        return restaurants

    def _write_cache(self, restaurants: list[Restaurant]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        frame = restaurants_to_frame(restaurants)
        frame.to_parquet(self.cache_path, index=False)
        logger.info("Wrote cleaned cache (%s rows) → %s", len(restaurants), self.cache_path)

    def _load_from_source(self) -> tuple[list[Restaurant], dict[str, float]]:
        source = self.settings.dataset_name
        source_path = Path(source)
        if source_path.exists() and source_path.is_file():
            logger.info("Loading dataset from local file %s", source_path)
            if source_path.suffix.lower() == ".csv":
                df = pd.read_csv(source_path)
            elif source_path.suffix.lower() in {".parquet", ".pq"}:
                df = pd.read_parquet(source_path)
            else:
                raise ValueError(f"Unsupported local dataset format: {source_path}")
            return normalize_dataframe(df, self.settings)

        try:
            from datasets import load_dataset
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The `datasets` package is required to download from Hugging Face"
            ) from exc

        try:
            logger.info("Downloading Hugging Face dataset %s", source)
            dataset = load_dataset(source, split="train")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to load dataset '{source}'. "
                "Check the dataset id / network, or point DATASET_NAME at a local "
                f"CSV/Parquet, or use an existing cache at {self.cache_path}."
            ) from exc

        df = dataset.to_pandas()
        return normalize_dataframe(df, self.settings)
