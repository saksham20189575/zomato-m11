"""FastAPI JSON API for TasteRank recommendations.

Reuses RecommendationService unchanged — presentation / transport only.
API keys stay server-side via Settings / .env (never exposed to the browser).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from recommender.config import get_settings
from recommender.engine import RecommendationEngine
from recommender.filters import CandidateFilter
from recommender.llm_client import LLMError, MockLLMClient
from recommender.models import BudgetBand, UserPreferences
from recommender.repository import RestaurantRepository
from recommender.service import (
    RecommendationService,
    ServiceResult,
    create_recommendation_service,
    recommend_with_mock,
)

_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def parse_cors_origins(raw: str | None = None) -> list[str]:
    """Parse comma-separated CORS origins from env (or an explicit string).

    Trailing slashes are stripped — browsers send Origin without a path, so
    ``https://app.vercel.app/`` would otherwise never match.
    """
    if raw is None:
        value = os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
    else:
        value = raw
    origins: list[str] = []
    for part in value.split(","):
        origin = part.strip().rstrip("/")
        if origin:
            origins.append(origin)
    return origins


app = FastAPI(
    title="TasteRank API",
    description="Grounded restaurant recommendations over the Zomato corpus.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    """Preferences plus optional offline mock flag."""

    location: str = Field(min_length=1)
    budget: BudgetBand
    cuisine: str | None = None
    min_rating: float = Field(default=4.0, ge=0.0, le=5.0)
    additional_preferences: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    mock: bool = False


class MetaResponse(BaseModel):
    locations: list[str]
    cuisines: list[str]
    default_top_k: int
    max_candidates: int
    has_llm_key: bool


@lru_cache(maxsize=1)
def _live_service() -> RecommendationService:
    return create_recommendation_service(settings=get_settings())


@lru_cache(maxsize=1)
def _mock_service() -> RecommendationService:
    settings = get_settings()
    return RecommendationService(
        repository=RestaurantRepository(settings=settings),
        candidate_filter=CandidateFilter(settings=settings),
        engine=RecommendationEngine(
            MockLLMClient('{"recommendations":[]}'),
            settings=settings,
        ),
        settings=settings,
    )


@lru_cache(maxsize=1)
def _meta_payload() -> tuple[tuple[str, ...], tuple[str, ...]]:
    repo = RestaurantRepository(settings=get_settings())
    return tuple(repo.distinct_locations()), tuple(repo.distinct_cuisines())


@app.get("/health")
def health() -> dict[str, Literal["ok"]]:
    return {"status": "ok"}


@app.get("/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    settings = get_settings()
    locations, cuisines = _meta_payload()
    return MetaResponse(
        locations=list(locations),
        cuisines=list(cuisines),
        default_top_k=settings.default_top_k,
        max_candidates=settings.max_candidates,
        has_llm_key=bool(settings.llm_api_key),
    )


@app.post("/recommend", response_model=ServiceResult)
def recommend(body: RecommendRequest) -> ServiceResult:
    prefs = UserPreferences(
        location=body.location,
        budget=body.budget,
        cuisine=body.cuisine,
        min_rating=body.min_rating,
        additional_preferences=body.additional_preferences,
        top_k=body.top_k,
    )
    try:
        if body.mock:
            return recommend_with_mock(_mock_service(), prefs)
        return _live_service().recommend(prefs)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface as 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc
