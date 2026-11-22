"""Parse and validate LLM recommendation responses (Phase 3)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from recommender.models import (
    Recommendation,
    RecommendationResult,
    RecommendationSource,
    Restaurant,
)

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)
_FALLBACK_EXPLANATION = (
    "Matched your filters; ranked by rating (LLM unavailable or response invalid)."
)


class ParseError(Exception):
    """Raised when the LLM payload cannot be turned into grounded recommendations."""


def _strip_fences_and_extract(text: str) -> str:
    """Pull a JSON object out of raw model text (fences / leading prose)."""
    stripped = text.strip()
    if not stripped:
        raise ParseError("Empty LLM response")

    fence = _FENCE_RE.search(stripped)
    if fence:
        return fence.group(1).strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]

    raise ParseError("No JSON object found in LLM response")


def _light_json_repair(raw: str) -> str:
    """Best-effort fixes for common LLM JSON slips (trailing commas)."""
    repaired = re.sub(r",\s*}", "}", raw)
    repaired = re.sub(r",\s*]", "]", repaired)
    return repaired


def _load_json(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            data = json.loads(_light_json_repair(raw))
        except json.JSONDecodeError as exc:
            raise ParseError(f"Malformed JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ParseError("LLM JSON root must be an object")
    return data


def build_fallback_result(
    candidates: list[Restaurant],
    *,
    top_k: int,
    note: str | None = None,
    summary: str | None = None,
) -> RecommendationResult:
    """Heuristic rank by rating/votes when the LLM path fails (RP-16 / SV-03)."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    ranked = sorted(candidates, key=lambda r: (-r.rating, -r.votes, r.id))
    picks = ranked[:top_k]
    recommendations = [
        Recommendation(
            restaurant_id=r.id,
            name=r.name,
            rank=i,
            cuisine=r.cuisine_display,
            rating=r.rating,
            estimated_cost=r.cost,
            explanation=_FALLBACK_EXPLANATION,
        )
        for i, r in enumerate(picks, start=1)
    ]
    return RecommendationResult(
        summary=summary
        or "Recommendations ranked by rating because the LLM path was unavailable.",
        recommendations=recommendations,
        source=RecommendationSource.FALLBACK,
        note=note
        or "Fallback: matched your filters; LLM unavailable or returned invalid data.",
    )


class ResponseParser:
    """Parse JSON recommendations and drop hallucinated restaurants."""

    def parse(
        self,
        raw_text: str,
        candidates: list[Restaurant],
        *,
        top_k: int,
    ) -> RecommendationResult:
        if not candidates:
            raise ParseError("Cannot parse recommendations without candidates")
        if top_k < 1:
            raise ParseError("top_k must be >= 1")

        by_id = {r.id: r for r in candidates}
        payload = _load_json(_strip_fences_and_extract(raw_text))
        rows = payload.get("recommendations")
        if rows is None:
            raise ParseError("Missing 'recommendations' key")
        if not isinstance(rows, list):
            raise ParseError("'recommendations' must be a list")
        if not rows:
            raise ParseError("Empty 'recommendations' array")

        seen: set[str] = set()
        grounded: list[tuple[int | None, Recommendation]] = []

        for row in rows:
            if not isinstance(row, dict):
                continue
            restaurant_id = row.get("restaurant_id") or row.get("id")
            if not isinstance(restaurant_id, str) or not restaurant_id.strip():
                logger.warning("Dropping recommendation with missing restaurant_id")
                continue
            restaurant_id = restaurant_id.strip()
            if restaurant_id not in by_id:
                logger.warning(
                    "Dropping hallucinated restaurant_id not in candidates: %s",
                    restaurant_id,
                )
                continue
            if restaurant_id in seen:
                logger.warning("Dropping duplicate restaurant_id: %s", restaurant_id)
                continue
            seen.add(restaurant_id)

            restaurant = by_id[restaurant_id]
            explanation = row.get("explanation")
            if not isinstance(explanation, str) or not explanation.strip():
                explanation = (
                    f"Matches your filters with rating {restaurant.rating} "
                    f"and cuisines {restaurant.cuisine_display}."
                )
            else:
                explanation = explanation.strip()

            rank_raw = row.get("rank")
            rank_hint: int | None
            try:
                rank_hint = int(rank_raw) if rank_raw is not None else None
            except (TypeError, ValueError):
                rank_hint = None

            # Prefer dataset fields over LLM-copied values (RP-06 / RP-14).
            grounded.append(
                (
                    rank_hint,
                    Recommendation(
                        restaurant_id=restaurant.id,
                        name=restaurant.name,
                        rank=1,  # reassigned after sort
                        cuisine=restaurant.cuisine_display,
                        rating=restaurant.rating,
                        estimated_cost=restaurant.cost,
                        explanation=explanation,
                    ),
                )
            )

        if not grounded:
            raise ParseError("All recommendations were invalid or hallucinated")

        # Stable order: explicit rank ascending, else original grounded order.
        indexed = list(enumerate(grounded))
        indexed.sort(
            key=lambda item: (
                item[1][0] is None,
                item[1][0] if item[1][0] is not None else 10**9,
                item[0],
            )
        )

        recommendations: list[Recommendation] = []
        for display_rank, (_, (_, rec)) in enumerate(indexed[:top_k], start=1):
            recommendations.append(rec.model_copy(update={"rank": display_rank}))

        summary = payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            summary = None
        else:
            summary = summary.strip()

        return RecommendationResult(
            summary=summary,
            recommendations=recommendations,
            source=RecommendationSource.LLM,
        )
