"""End-to-end recommendation orchestration (Phase 4)."""

from __future__ import annotations

import json
import logging
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from recommender.config import Settings, get_settings
from recommender.engine import RecommendationEngine
from recommender.filters import CandidateFilter, EmptyReasonCode
from recommender.llm_client import GroqLLMClient, LLMClient, MockLLMClient
from recommender.models import RecommendationResult, UserPreferences
from recommender.repository import RestaurantRepository

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Outcome of a recommendation request."""

    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


class ServiceResult(BaseModel):
    """UI-facing envelope for CLI / future web layer."""

    status: ServiceStatus
    preferences: UserPreferences | None = None
    shortlist_size: int = 0
    result: RecommendationResult | None = None
    empty_reason_code: EmptyReasonCode | None = None
    message: str | None = None
    model_name: str | None = Field(
        default=None,
        description="Configured LLM model id (never the API key)",
    )


class RecommendationService:
    """Validate prefs → load → filter → (empty?) → engine → return."""

    def __init__(
        self,
        repository: RestaurantRepository,
        candidate_filter: CandidateFilter,
        engine: RecommendationEngine,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository
        self.candidate_filter = candidate_filter
        self.engine = engine
        self.settings = settings or get_settings()

    def recommend(
        self,
        preferences: UserPreferences | dict,
    ) -> ServiceResult:
        """Run the full pipeline. Never raises for empty shortlist / LLM failure."""
        try:
            prefs = self._validate_preferences(preferences)
        except ValidationError as exc:
            return ServiceResult(
                status=ServiceStatus.ERROR,
                message=f"Invalid preferences: {exc.errors()[0]['msg']}",
                model_name=self.settings.llm_model,
            )

        try:
            restaurants = self.repository.load()
        except Exception as exc:  # noqa: BLE001 — user-facing load failure
            logger.exception("Restaurant corpus load failed")
            return ServiceResult(
                status=ServiceStatus.ERROR,
                preferences=prefs,
                message=f"Could not load restaurant data: {exc}",
                model_name=self.settings.llm_model,
            )

        filtered = self.candidate_filter.filter(restaurants, prefs)
        if filtered.is_empty:
            logger.info(
                "Empty shortlist reason=%s corpus=%s",
                filtered.reason_code,
                len(restaurants),
            )
            return ServiceResult(
                status=ServiceStatus.EMPTY,
                preferences=prefs,
                shortlist_size=0,
                empty_reason_code=filtered.reason_code,
                message=filtered.message
                or "No restaurants matched all preferences.",
                model_name=self.settings.llm_model,
            )

        logger.info(
            "Shortlist size=%s model=%s top_k=%s",
            len(filtered.restaurants),
            self.settings.llm_model,
            prefs.top_k or self.settings.default_top_k,
        )

        # Engine already falls back on LLM/parse failure (no stack dump).
        result = self.engine.recommend(prefs, filtered.restaurants)
        logger.info(
            "Recommendations source=%s count=%s",
            result.source.value,
            len(result.recommendations),
        )
        return ServiceResult(
            status=ServiceStatus.SUCCESS,
            preferences=prefs,
            shortlist_size=len(filtered.restaurants),
            result=result,
            model_name=self.settings.llm_model,
        )

    @staticmethod
    def _validate_preferences(
        preferences: UserPreferences | dict,
    ) -> UserPreferences:
        if isinstance(preferences, UserPreferences):
            return preferences
        return UserPreferences.model_validate(preferences)


def create_recommendation_service(
    settings: Settings | None = None,
    *,
    llm_client: LLMClient | None = None,
    use_mock_llm: bool = False,
    mock_response: str | None = None,
) -> RecommendationService:
    """Wire repository, filter, and engine with a live or mock LLM client."""
    settings = settings or get_settings()
    repository = RestaurantRepository(settings=settings)
    candidate_filter = CandidateFilter(settings=settings)

    if llm_client is not None:
        client = llm_client
    elif use_mock_llm:
        client = MockLLMClient(
            mock_response
            or (
                '{"summary":"Mock recommendations.","recommendations":[]}'
            )
        )
    else:
        client = GroqLLMClient(settings=settings)

    engine = RecommendationEngine(client, settings=settings)
    return RecommendationService(
        repository=repository,
        candidate_filter=candidate_filter,
        engine=engine,
        settings=settings,
    )


def recommend_with_mock(
    service: RecommendationService,
    preferences: UserPreferences,
) -> ServiceResult:
    """Offline path: real filter shortlist, then mock-rank (no Groq call).

    Shared by the CLI (`--mock`) and Streamlit UI so presentation stays thin.
    """
    try:
        restaurants = service.repository.load()
    except Exception as exc:  # noqa: BLE001 — user-facing load failure
        return ServiceResult(
            status=ServiceStatus.ERROR,
            preferences=preferences,
            message=f"Could not load restaurant data: {exc}",
            model_name=service.settings.llm_model,
        )

    filtered = service.candidate_filter.filter(restaurants, preferences)
    if filtered.is_empty:
        return ServiceResult(
            status=ServiceStatus.EMPTY,
            preferences=preferences,
            shortlist_size=0,
            empty_reason_code=filtered.reason_code,
            message=filtered.message,
            model_name="mock",
        )

    top_k = preferences.top_k or service.settings.default_top_k
    top_k = min(top_k, len(filtered.restaurants))
    payload = {
        "summary": "Offline mock ranking (no Groq call).",
        "recommendations": [
            {
                "restaurant_id": r.id,
                "rank": i,
                "explanation": (
                    "Mock rank: matches "
                    + (
                        f"{preferences.cuisine} in "
                        if preferences.cuisine
                        else "preferences in "
                    )
                    + f"{preferences.location} at rating {r.rating}."
                ),
            }
            for i, r in enumerate(filtered.restaurants[:top_k], start=1)
        ],
    }
    engine = RecommendationEngine(
        MockLLMClient(json.dumps(payload)),
        settings=service.settings,
    )
    result = engine.recommend(preferences, filtered.restaurants)
    return ServiceResult(
        status=ServiceStatus.SUCCESS,
        preferences=preferences,
        shortlist_size=len(filtered.restaurants),
        result=result,
        model_name="mock",
    )
