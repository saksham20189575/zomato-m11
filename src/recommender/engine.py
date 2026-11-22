"""LLM recommendation engine: prompt → complete → parse → fallback (Phase 3)."""

from __future__ import annotations

import logging

from recommender.config import Settings, get_settings
from recommender.llm_client import LLMClient, LLMError
from recommender.models import RecommendationResult, Restaurant, UserPreferences
from recommender.parser import ParseError, ResponseParser, build_fallback_result
from recommender.prompts import PromptBuilder, PromptPayload

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Rank a non-empty candidate shortlist with explanations.

    Phase 4's ``RecommendationService`` should call this after filtering.
    Empty shortlists must be handled upstream (no LLM call).
    """

    def __init__(
        self,
        llm_client: LLMClient,
        *,
        prompt_builder: PromptBuilder | None = None,
        parser: ResponseParser | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.parser = parser or ResponseParser()
        self.settings = settings or get_settings()

    def recommend(
        self,
        preferences: UserPreferences,
        candidates: list[Restaurant],
    ) -> RecommendationResult:
        if not candidates:
            raise ValueError(
                "RecommendationEngine requires a non-empty candidate list; "
                "handle empty shortlists before calling the LLM"
            )

        top_k = preferences.top_k or self.settings.default_top_k
        top_k = min(top_k, len(candidates))

        prompt = self.prompt_builder.build(
            preferences, candidates, top_k=top_k
        )
        return self._complete_and_parse(prompt, candidates, top_k=top_k)

    def _complete_and_parse(
        self,
        prompt: PromptPayload,
        candidates: list[Restaurant],
        *,
        top_k: int,
    ) -> RecommendationResult:
        try:
            raw = self.llm_client.complete(prompt)
        except LLMError as exc:
            logger.warning("LLM call failed; using fallback: %s", exc)
            return build_fallback_result(
                candidates,
                top_k=top_k,
                note=f"Fallback after LLM error: {exc}",
            )

        try:
            return self.parser.parse(raw, candidates, top_k=top_k)
        except ParseError as exc:
            logger.warning("LLM parse failed; using fallback: %s", exc)
            return build_fallback_result(
                candidates,
                top_k=top_k,
                note=f"Fallback after invalid LLM response: {exc}",
            )
