"""CLI entrypoint for the restaurant recommendation app."""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from typing import Any

from recommender.config import get_settings
from recommender.engine import RecommendationEngine
from recommender.filters import CandidateFilter
from recommender.llm_client import LLMError, MockLLMClient
from recommender.models import BudgetBand, RecommendationSource, UserPreferences
from recommender.repository import RestaurantRepository
from recommender.service import (
    RecommendationService,
    ServiceResult,
    ServiceStatus,
    create_recommendation_service,
    recommend_with_mock,
)

_BUDGET_CHOICES = tuple(b.value for b in BudgetBand)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zomato-recommend",
        description=(
            "AI-powered restaurant recommendations (filter shortlist + Groq ranking)."
        ),
    )
    parser.add_argument("--location", help="City or locality (e.g. Bangalore)")
    parser.add_argument(
        "--budget",
        choices=_BUDGET_CHOICES,
        help="Budget band: low | medium | high",
    )
    parser.add_argument(
        "--cuisine",
        help="Preferred cuisine (e.g. Chinese); omit for any cuisine",
    )
    parser.add_argument(
        "--min-rating",
        type=float,
        dest="min_rating",
        help="Minimum rating 0–5 (default: 4.0 in interactive mode)",
    )
    parser.add_argument(
        "--extras",
        dest="additional_preferences",
        help="Optional free-text preferences for the LLM",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        dest="top_k",
        help="Number of recommendations (default from config)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use MockLLMClient instead of live Groq (offline demo)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Force interactive prompts even if flags are set",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log shortlist size / model at INFO (never secrets)",
    )
    return parser


def _prompt_line(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    raw = input(f"{label}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    return raw


def collect_preferences_interactive(
    defaults: dict[str, Any] | None = None,
) -> UserPreferences:
    """Prompt for prefs; EOF / Ctrl-C exit cleanly (UI-20)."""
    defaults = defaults or {}
    print("Enter your restaurant preferences (Ctrl-C to cancel).\n")
    location = _prompt_line("Location", defaults.get("location") or "Bangalore")
    budget = _prompt_line(
        "Budget (low/medium/high)",
        defaults.get("budget") or BudgetBand.MEDIUM.value,
    )
    cuisine = _prompt_line(
        "Cuisine (optional, blank = any)",
        defaults.get("cuisine") or "",
    )
    min_rating_raw = _prompt_line(
        "Minimum rating (0-5)",
        str(
            defaults.get("min_rating")
            if defaults.get("min_rating") is not None
            else 4.0
        ),
    )
    extras = _prompt_line(
        "Additional preferences (optional)",
        defaults.get("additional_preferences") or "",
    )
    top_k_default = defaults.get("top_k")
    top_k_raw = _prompt_line(
        "How many recommendations?",
        str(top_k_default) if top_k_default is not None else "",
    )

    payload: dict[str, Any] = {
        "location": location,
        "budget": budget,
        "cuisine": cuisine or None,
        "min_rating": float(min_rating_raw),
        "additional_preferences": extras or None,
    }
    if top_k_raw.strip():
        payload["top_k"] = int(top_k_raw)
    return UserPreferences.model_validate(payload)


def preferences_from_args(args: argparse.Namespace) -> UserPreferences | None:
    """Build prefs from CLI flags when the required set is present.

    Cuisine is optional (None = any cuisine).
    """
    required = (args.location, args.budget, args.min_rating)
    if any(v is None for v in required):
        return None
    return UserPreferences(
        location=args.location,
        budget=args.budget,
        cuisine=args.cuisine,
        min_rating=args.min_rating,
        additional_preferences=args.additional_preferences,
        top_k=args.top_k,
    )


def format_results(service_result: ServiceResult) -> str:
    """Pretty-print recommendations for the terminal."""
    lines: list[str] = []
    prefs = service_result.preferences

    lines.append("=" * 60)
    lines.append("Restaurant Recommendations")
    lines.append("=" * 60)

    if prefs is not None:
        extras = (
            f" | extras={prefs.additional_preferences!r}"
            if prefs.additional_preferences
            else ""
        )
        cuisine_label = prefs.cuisine or "any"
        lines.append(
            f"Prefs: {prefs.location} | {prefs.budget.value} | {cuisine_label} | "
            f"min_rating>={prefs.min_rating}{extras}"
        )

    if service_result.status == ServiceStatus.ERROR:
        lines.append("")
        lines.append(f"Error: {service_result.message}")
        return "\n".join(lines)

    if service_result.status == ServiceStatus.EMPTY:
        lines.append("")
        lines.append("No matching restaurants.")
        if service_result.message:
            lines.append(service_result.message)
        lines.append(
            "Tip: broaden location, cuisine, budget, or lower min_rating."
        )
        return "\n".join(lines)

    result = service_result.result
    assert result is not None
    if result.source == RecommendationSource.FALLBACK:
        source_label = "Fallback (heuristic)"
    elif service_result.model_name == "mock":
        source_label = "Mock LLM"
    else:
        source_label = "Groq LLM"
    lines.append(
        f"Shortlist: {service_result.shortlist_size} | "
        f"Model: {service_result.model_name or 'n/a'} | "
        f"Source: {source_label}"
    )
    if result.note:
        lines.append(f"Note: {result.note}")
    if result.summary:
        lines.append("")
        lines.append("Summary:")
        lines.extend(textwrap.wrap(result.summary, width=72) or [result.summary])

    lines.append("")
    if not result.recommendations:
        lines.append("No recommendations returned.")
        return "\n".join(lines)

    for rec in result.recommendations:
        cost = (
            f"{rec.estimated_cost:.0f}"
            if rec.estimated_cost is not None
            else "n/a"
        )
        lines.append(f"{rec.rank}. {rec.name}")
        lines.append(f"   {rec.cuisine} | rating {rec.rating} | cost ~{cost}")
        lines.append(
            textwrap.fill(
                rec.explanation,
                width=72,
                initial_indent="   Why: ",
                subsequent_indent="         ",
            )
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    settings = get_settings()

    try:
        if args.interactive or preferences_from_args(args) is None:
            defaults = {
                "location": args.location,
                "budget": args.budget,
                "cuisine": args.cuisine,
                "min_rating": args.min_rating,
                "additional_preferences": args.additional_preferences,
                "top_k": args.top_k,
            }
            prefs = collect_preferences_interactive(defaults)
        else:
            prefs = preferences_from_args(args)
            assert prefs is not None
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        return 130
    except (ValueError, TypeError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2

    try:
        if args.mock:
            # Repository/filter only; LLM is mocked after shortlist is known.
            service = RecommendationService(
                repository=RestaurantRepository(settings=settings),
                candidate_filter=CandidateFilter(settings=settings),
                engine=RecommendationEngine(
                    MockLLMClient('{"recommendations":[]}'),
                    settings=settings,
                ),
                settings=settings,
            )
            outcome = recommend_with_mock(service, prefs)
        else:
            service = create_recommendation_service(settings=settings)
            outcome = service.recommend(prefs)
    except LLMError as exc:
        print(f"LLM configuration error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    print(format_results(outcome))
    return 1 if outcome.status == ServiceStatus.ERROR else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
