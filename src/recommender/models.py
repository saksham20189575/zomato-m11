"""Domain models: preferences, restaurants, and shared enums."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BudgetBand(str, Enum):
    """User budget preference and restaurant cost band."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserPreferences(BaseModel):
    """Structured preferences collected from the user (CLI / UI)."""

    location: str = Field(min_length=1, description="City or locality")
    budget: BudgetBand
    cuisine: str | None = Field(
        default=None,
        description="Preferred cuisine; None / omitted = any cuisine",
    )
    min_rating: float = Field(ge=0.0, le=5.0, description="Minimum acceptable rating")
    additional_preferences: str | None = Field(
        default=None,
        description="Optional free-text extras for the LLM",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        description="Number of recommendations; None → config default",
    )

    @field_validator("location", mode="before")
    @classmethod
    def _strip_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("cuisine", "additional_preferences", mode="before")
    @classmethod
    def _empty_optional_text_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("budget", mode="before")
    @classmethod
    def _normalize_budget(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class Restaurant(BaseModel):
    """Canonical restaurant record after ingestion / normalization."""

    id: str
    name: str
    location: str
    cuisines: list[str]
    cost: float | None = None
    cost_band: BudgetBand | None = None
    rating: float
    votes: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def cuisine_display(self) -> str:
        return ", ".join(self.cuisines)


class RecommendationSource(str, Enum):
    """How a recommendation list was produced."""

    LLM = "llm"
    FALLBACK = "fallback"


class Recommendation(BaseModel):
    """Single ranked restaurant with a human-readable explanation."""

    restaurant_id: str
    name: str
    rank: int = Field(ge=1)
    cuisine: str
    rating: float
    estimated_cost: float | None = None
    explanation: str = Field(min_length=1)


class RecommendationResult(BaseModel):
    """Parsed / grounded recommendation payload for the UI."""

    summary: str | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    source: RecommendationSource = RecommendationSource.LLM
    note: str | None = Field(
        default=None,
        description="Optional UX note (e.g. fallback / truncated)",
    )
