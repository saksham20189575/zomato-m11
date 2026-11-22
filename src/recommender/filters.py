"""Deterministic candidate filtering (no LLM dependency).

Hard filters (all must pass): location, cuisine (if set), min_rating, budget/cost_band.
Soft pre-rank: rating desc → votes desc → id asc, then truncate to MAX_CANDIDATES.

Relaxation: optional and **off by default**. When enabled later, document which
constraint was relaxed; never invent restaurants (see edge-case CF-08).
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field

from recommender.config import Settings, get_settings
from recommender.models import Restaurant, UserPreferences

# Avoid ultra-short contains matches like "Al" → unrelated localities (CF-02).
_MIN_CONTAINS_LEN = 3


class EmptyReasonCode(str, Enum):
    """Why the shortlist is empty (explicit; no silent inventing)."""

    NO_LOCATION_MATCH = "no_location_match"
    NO_CUISINE_MATCH = "no_cuisine_match"
    NO_RATING_MATCH = "no_rating_match"
    NO_BUDGET_MATCH = "no_budget_match"
    NO_MATCH = "no_match"


_EMPTY_MESSAGES: dict[EmptyReasonCode, str] = {
    EmptyReasonCode.NO_LOCATION_MATCH: (
        "No restaurants matched that location. Try a city (e.g. Bangalore) "
        "or a known locality."
    ),
    EmptyReasonCode.NO_CUISINE_MATCH: (
        "No restaurants matched that cuisine in the filtered set. "
        "Try a broader cuisine name."
    ),
    EmptyReasonCode.NO_RATING_MATCH: (
        "No restaurants met the minimum rating. Try lowering min_rating."
    ),
    EmptyReasonCode.NO_BUDGET_MATCH: (
        "No restaurants matched that budget band. Try a different budget."
    ),
    EmptyReasonCode.NO_MATCH: (
        "No restaurants matched all preferences. Broaden location, cuisine, "
        "budget, or min_rating."
    ),
}


class FilterResult(BaseModel):
    """Shortlist plus an explicit empty-result explanation when applicable."""

    restaurants: list[Restaurant] = Field(default_factory=list)
    reason_code: EmptyReasonCode | None = None
    message: str | None = None

    @property
    def is_empty(self) -> bool:
        return len(self.restaurants) == 0


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def matches_location(restaurant_location: str, preferred: str) -> bool:
    """Case-insensitive location match against locality/city string.

    Uses substring contains for queries of length >= 3.
    Shorter queries require a whole-token match to limit false positives.
    """
    haystack = _normalize_text(restaurant_location)
    needle = _normalize_text(preferred)
    if not needle or not haystack:
        return False
    if len(needle) < _MIN_CONTAINS_LEN:
        tokens = re.split(r"[^a-z0-9]+", haystack)
        return needle in tokens
    return needle in haystack


def matches_cuisine(cuisines: list[str], preferred: str) -> bool:
    """Match preferred cuisine against restaurant cuisine tokens.

    - Comma-separated prefs: match if **any** preferred token matches (documented).
    - Match is case-insensitive word-boundary (so ``Indian`` matches
      ``North Indian``, but ``Chi`` does not match ``Chinese``).
    """
    prefs = [p.strip() for p in preferred.split(",") if p.strip()]
    if not prefs:
        return False

    for pref in prefs:
        pattern = re.compile(rf"\b{re.escape(_normalize_text(pref))}\b", re.IGNORECASE)
        for cuisine in cuisines:
            if pattern.search(_normalize_text(cuisine)):
                return True
    return False


def matches_min_rating(rating: float, min_rating: float) -> bool:
    """Inclusive minimum rating threshold."""
    return rating >= min_rating


def matches_budget(restaurant: Restaurant, prefs: UserPreferences) -> bool:
    """Hard budget match on cost_band; null/unknown band never matches."""
    if restaurant.cost_band is None:
        return False
    return restaurant.cost_band == prefs.budget


class CandidateFilter:
    """Apply hard preference filters and truncate to MAX_CANDIDATES.

    Pure / deterministic for the same corpus + preferences (CF-13).
    Does not call or import any LLM client.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        max_candidates: int | None = None,
        enable_relaxation: bool = False,
    ) -> None:
        self.settings = settings or get_settings()
        self.max_candidates = max_candidates or self.settings.max_candidates
        # Reserved for a future ordered relaxation path; kept off for v1.
        self.enable_relaxation = enable_relaxation

    def filter(
        self,
        restaurants: list[Restaurant],
        preferences: UserPreferences,
    ) -> FilterResult:
        """Return a preference-aligned shortlist (possibly empty + reason)."""
        if self.enable_relaxation:
            # Documented hook only — do not silently relax hard constraints in v1.
            raise NotImplementedError(
                "Preference relaxation is disabled for v1; leave enable_relaxation=False"
            )

        after_location = [
            r for r in restaurants if matches_location(r.location, preferences.location)
        ]
        if not after_location:
            return self._empty(EmptyReasonCode.NO_LOCATION_MATCH)

        if preferences.cuisine:
            after_cuisine = [
                r
                for r in after_location
                if matches_cuisine(r.cuisines, preferences.cuisine)
            ]
            if not after_cuisine:
                return self._empty(EmptyReasonCode.NO_CUISINE_MATCH)
        else:
            after_cuisine = after_location

        after_rating = [
            r
            for r in after_cuisine
            if matches_min_rating(r.rating, preferences.min_rating)
        ]
        if not after_rating:
            return self._empty(EmptyReasonCode.NO_RATING_MATCH)

        after_budget = [r for r in after_rating if matches_budget(r, preferences)]
        if not after_budget:
            return self._empty(EmptyReasonCode.NO_BUDGET_MATCH)

        ranked = self._rank(after_budget)
        shortlist = ranked[: self.max_candidates]
        return FilterResult(restaurants=shortlist)

    @staticmethod
    def _rank(restaurants: list[Restaurant]) -> list[Restaurant]:
        """Soft pre-rank: higher rating, then votes; id for stable ties."""
        return sorted(
            restaurants,
            key=lambda r: (-r.rating, -r.votes, r.id),
        )

    @staticmethod
    def _empty(code: EmptyReasonCode) -> FilterResult:
        return FilterResult(
            restaurants=[],
            reason_code=code,
            message=_EMPTY_MESSAGES[code],
        )
