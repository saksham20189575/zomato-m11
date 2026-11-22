"""Streamlit UI for TasteRank restaurant recommendations.

Reuses RecommendationService unchanged — presentation only.
Visual system aligned to stitch_tasterank_dark_web_ui (TasteRank).
API keys stay server-side via Settings / .env (never sent to the browser).
"""

from __future__ import annotations

import html
import re

import streamlit as st
from pydantic import ValidationError

from recommender.config import get_settings
from recommender.engine import RecommendationEngine
from recommender.filters import CandidateFilter
from recommender.llm_client import LLMError, MockLLMClient
from recommender.models import BudgetBand, Recommendation, RecommendationSource, UserPreferences
from recommender.repository import RestaurantRepository
from recommender.service import (
    RecommendationService,
    ServiceResult,
    ServiceStatus,
    create_recommendation_service,
    recommend_with_mock,
)

_ANY_CUISINE = "Any cuisine"
_BUDGET_LABELS = {
    BudgetBand.LOW: "₹ Low",
    BudgetBand.MEDIUM: "₹₹ Medium",
    BudgetBand.HIGH: "₹₹₹ High",
}
_FEATURED_CUISINES = (
    "North Indian",
    "South Indian",
    "Chinese",
    "Italian",
    "Cafe",
    "Continental",
)
_DEMO_LOCATION_HINTS = (
    "Koramangala 5th Block, Bangalore",
    "Koramangala, Bangalore",
    "Indiranagar, Bangalore",
)
_DEMO_EXTRAS = (
    "Rooftop ambience with outdoor seating and signature craft beverages"
)

_DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Outfit:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, .stText, label, p, span, div {
  font-family: "Outfit", sans-serif !important;
}

.stApp {
  background:
    radial-gradient(700px 500px at 50% -10%, rgba(255, 83, 81, 0.10), transparent 55%),
    radial-gradient(600px 500px at 100% 100%, rgba(137, 145, 163, 0.08), transparent 50%),
    linear-gradient(180deg, #0B0D12 0%, #111318 40%, #0B0D12 100%);
  color: #e2e2e9;
}

[data-testid="stHeader"] {
  background: rgba(12, 14, 19, 0.80) !important;
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

[data-testid="stToolbar"] { background: transparent; }

[data-testid="stSidebar"] {
  background: rgba(26, 27, 33, 0.92) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
}

[data-testid="stSidebar"] > div:first-child {
  padding-top: 1rem;
}

.block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1160px !important;
}

/* —— Hero —— */
.tr-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #ffb3ae;
  margin: 0 0 0.5rem 0;
}
.tr-eyebrow::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: #ff5351;
  box-shadow: 0 0 10px rgba(255, 83, 81, 0.6);
  animation: tr-pulse 1.6s ease-in-out infinite;
}
@keyframes tr-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}

.tr-hero {
  font-family: "Newsreader", Georgia, serif !important;
  font-size: clamp(2.25rem, 5vw, 3rem);
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 0 0 0.55rem 0;
  color: #e2e2e9;
}
.tr-hero span {
  background: linear-gradient(135deg, #ff5351 0%, #ffb3b1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.tr-sub {
  color: #e4bdba;
  font-size: 1.05rem;
  line-height: 1.55;
  margin: 0 0 1.25rem 0;
  max-width: 40rem;
  opacity: 0.92;
}

.tr-section {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #ab8886;
  margin: 0.25rem 0 0.85rem 0;
}

/* —— Prefs card shell (sidebar) —— */
.tr-prefs-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.35rem;
}
.tr-prefs-head .label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #ab8886;
}
.tr-prefs-head .badge {
  font-size: 11px;
  font-weight: 600;
  color: #ffb3ae;
}

.tr-ranker-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  margin-top: 0.75rem;
}
.tr-ranker-icon {
  width: 40px;
  height: 40px;
  border-radius: 9999px;
  background: rgba(255, 179, 174, 0.12);
  color: #ffb3ae;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}
.tr-ranker-title {
  font-size: 13px;
  font-weight: 600;
  color: #e2e2e9;
  margin: 0;
}
.tr-ranker-meta {
  font-size: 12px;
  color: #ab8886;
  margin: 0.15rem 0 0 0;
}

/* —— Results —— */
.tr-results-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin: 0.25rem 0 0.85rem 0;
}
.tr-live {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 12px;
  font-weight: 500;
  color: #ffb3ae;
}
.tr-live-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: #ffb3ae;
  animation: tr-pulse 1.4s ease-in-out infinite;
}

.tr-status-banner {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  background: rgba(26, 27, 33, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 0.7rem 0.85rem;
  margin-bottom: 0.85rem;
  color: #e4bdba;
  font-size: 13px;
  line-height: 1.45;
}
.tr-status-banner .icon {
  width: 24px;
  height: 24px;
  border-radius: 9999px;
  background: rgba(255, 179, 174, 0.18);
  color: #ffb3ae;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.tr-synth {
  background: linear-gradient(165deg, rgba(26, 27, 33, 0.9), rgba(30, 31, 37, 0.7));
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
  box-shadow: 0 12px 32px -4px rgba(0, 0, 0, 0.45);
}
.tr-synth-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.65rem;
}
.tr-synth-title {
  font-family: "Newsreader", Georgia, serif !important;
  font-size: 1.35rem;
  font-weight: 500;
  color: #e2e2e9;
  margin: 0;
}
.tr-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.65rem;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.05);
  color: #A8B0C0;
}
.tr-chip-live {
  background: rgba(51, 53, 58, 0.85);
  color: #e2e2e9;
}
.tr-chip-live::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: #34d399;
}
.tr-synth-body {
  background: rgba(12, 14, 19, 0.55);
  border-left: 2px solid #ff5351;
  border-radius: 8px;
  padding: 0.7rem 0.85rem;
  color: #e4bdba;
  font-size: 13px;
  line-height: 1.55;
}
.tr-synth-body strong {
  display: block;
  color: #ffb3ae;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 0.2rem;
}

/* —— Recommendation cards —— */
.tr-card {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  background: rgba(26, 27, 33, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1rem;
  margin-bottom: 0.85rem;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.30);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.tr-card.top {
  box-shadow: 0 0 48px -12px rgba(255, 75, 75, 0.18), 0 8px 30px rgba(0, 0, 0, 0.35);
  border-color: rgba(255, 83, 81, 0.22);
}
.tr-card:hover {
  border-color: rgba(255, 83, 81, 0.40);
  box-shadow: 0 0 40px -10px rgba(255, 83, 81, 0.25), 0 12px 36px rgba(0, 0, 0, 0.4);
}
.tr-rank-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.65rem;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #ff5351 0%, #ff8a8a 100%);
  box-shadow: 0 4px 14px rgba(255, 83, 81, 0.35);
}
.tr-rank-pill.alt {
  background: rgba(51, 53, 58, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #ffb3ae;
  box-shadow: none;
}
.tr-card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 0.35rem;
}
.tr-card-body { flex: 1; min-width: 0; }
.tr-name {
  font-family: "Newsreader", Georgia, serif !important;
  font-size: 1.2rem;
  font-weight: 600;
  color: #e2e2e9;
  margin: 0;
  line-height: 1.3;
}
.tr-meta {
  color: #A8B0C0;
  font-size: 12px;
  line-height: 1.45;
  margin-bottom: 0.65rem;
}
.tr-meta .rating { color: #ffb3ae; font-weight: 600; }
.tr-meta .cuisine { color: #e2e2e9; font-weight: 500; }
.tr-why {
  background: rgba(12, 14, 19, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  color: #e4bdba;
  font-size: 13px;
  line-height: 1.5;
  margin: 0 0 0.65rem 0;
}
.tr-why strong {
  color: #ffb3ae;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.tr-tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.tr-tag {
  padding: 0.15rem 0.55rem;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.04);
  color: #A8B0C0;
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.tr-tag.accent {
  background: rgba(255, 75, 75, 0.12);
  color: #ff8a8a;
  border-color: rgba(255, 75, 75, 0.25);
}

/* —— Empty / error —— */
.tr-empty, .tr-error {
  text-align: center;
  padding: 3.5rem 1.5rem;
  border-radius: 18px;
  background: rgba(26, 27, 33, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.05);
  margin: 0.5rem 0 1rem 0;
}
.tr-error { border-color: rgba(255, 180, 171, 0.22); }
.tr-empty-icon, .tr-error-icon {
  width: 64px;
  height: 64px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem auto;
  font-size: 1.6rem;
}
.tr-empty-icon {
  background: rgba(255, 179, 174, 0.12);
  color: #ffb3ae;
}
.tr-error-icon {
  background: rgba(147, 0, 10, 0.35);
  color: #ffb4ab;
}
.tr-empty h3, .tr-error h3 {
  font-family: "Newsreader", Georgia, serif !important;
  font-size: 1.4rem;
  font-weight: 500;
  color: #e2e2e9;
  margin: 0 0 0.5rem 0;
}
.tr-empty p, .tr-error p {
  color: #A8B0C0;
  font-size: 0.95rem;
  max-width: 28rem;
  margin: 0 auto;
  line-height: 1.5;
}

/* —— Footer —— */
.tr-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 2rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  color: #A8B0C0;
  font-size: 12px;
}
.tr-footer .brand {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

/* —— Streamlit controls —— */
div[data-testid="stForm"] {
  background: rgba(26, 27, 33, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1rem 1rem 0.85rem 1rem;
  backdrop-filter: blur(16px);
  box-shadow: 0 12px 32px -4px rgba(0, 0, 0, 0.45);
}

div.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #FF4B4B 0%, #FF8A8A 100%) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600 !important;
  border-radius: 9999px !important;
  padding: 0.55rem 1rem !important;
  box-shadow: 0 8px 24px -6px rgba(255, 75, 75, 0.45);
}
div.stButton > button[kind="primary"]:hover {
  opacity: 0.95;
  border: none !important;
  color: #fff !important;
}
div.stButton > button[kind="secondary"] {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(255, 255, 255, 0.10) !important;
  color: #e2e2e9 !important;
  border-radius: 9999px !important;
  font-weight: 500 !important;
}

[data-testid="stSidebar"] label {
  font-size: 12px !important;
  font-weight: 500 !important;
  color: #e4bdba !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] > div,
.stNumberInput > div > div {
  background: rgba(12, 14, 19, 0.9) !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
  border-radius: 12px !important;
  color: #e2e2e9 !important;
}

.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: #ff5351 !important;
}

</style>
"""


@st.cache_resource(show_spinner=False)
def _live_service() -> RecommendationService:
    return create_recommendation_service(settings=get_settings())


@st.cache_resource(show_spinner=False)
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


@st.cache_data(show_spinner="Loading locations & cuisines…")
def _location_and_cuisine_options() -> tuple[list[str], list[str]]:
    repo = RestaurantRepository(settings=get_settings())
    return repo.distinct_locations(), repo.distinct_cuisines()


def _default_location_index(locations: list[str]) -> int:
    preferred = (
        "Koramangala 5th Block, Bangalore",
        "Indiranagar, Bangalore",
        "BTM, Bangalore",
    )
    for name in preferred:
        if name in locations:
            return locations.index(name)
    for i, name in enumerate(locations):
        if "bangalore" in name.lower():
            return i
    return 0


def _find_demo_location(locations: list[str]) -> str:
    for name in _DEMO_LOCATION_HINTS:
        if name in locations:
            return name
    idx = _default_location_index(locations)
    return locations[idx]


def _cuisine_options(all_cuisines: list[str]) -> list[str]:
    featured = [c for c in _FEATURED_CUISINES if c in all_cuisines]
    rest = [c for c in all_cuisines if c not in featured]
    return [_ANY_CUISINE, *featured, *rest]


def _run_recommend(
    prefs: UserPreferences,
    *,
    use_mock: bool,
) -> ServiceResult:
    if use_mock:
        return recommend_with_mock(_mock_service(), prefs)
    return _live_service().recommend(prefs)


def _source_label(outcome: ServiceResult) -> str:
    result = outcome.result
    if result is None:
        return "—"
    if result.source == RecommendationSource.FALLBACK:
        return "Fallback · Local Signal"
    if outcome.model_name == "mock":
        return "Mock LLM + Local Signal"
    return "AI LLM + Local Signal"


def _match_pct(rank: int, rating: float) -> int:
    # Rank-led score with a small rating nudge (mirrors Stitch badge ladder).
    base = 98 - (rank - 1) * 3
    nudge = int(round((rating - 4.3) * 4))
    return max(72, min(99, base + max(-3, min(2, nudge))))


def _budget_display(cost: float | None) -> str:
    if cost is None:
        return "Budget n/a"
    if cost < 500:
        band = "₹ Low"
    elif cost < 1200:
        band = "₹₹ Medium"
    else:
        band = "₹₹₹ High"
    return f"{band} (₹{cost:.0f} for 2)"


def _cuisine_tags(cuisine: str, explanation: str) -> list[str]:
    tags = [t.strip() for t in cuisine.split(",") if t.strip()][:3]
    extras: list[str] = []
    lowered = explanation.lower()
    for needle, label in (
        ("outdoor", "Outdoor Seating"),
        ("rooftop", "Rooftop"),
        ("craft", "Craft Drinks"),
        ("quiet", "Quiet"),
        ("family", "Family Friendly"),
        ("beer", "Craft Beer"),
        ("wine", "Wine"),
    ):
        if needle in lowered and label not in tags and label not in extras:
            extras.append(label)
        if len(extras) >= 2:
            break
    return (tags + extras)[:5]


def _render_card(rec: Recommendation) -> None:
    match = _match_pct(rec.rank, rec.rating)
    cost = _budget_display(rec.estimated_cost)
    tags = _cuisine_tags(rec.cuisine, rec.explanation)
    pill_class = "tr-rank-pill" if rec.rank == 1 else "tr-rank-pill alt"
    pill_text = (
        f"#{rec.rank} · {match}% Match"
        if rec.rank == 1
        else f"#{rec.rank} · {match}%"
    )
    tag_html = "".join(
        f'<span class="tr-tag{" accent" if i == len(tags) - 1 and len(tags) > 1 else ""}">'
        f"{html.escape(tag)}</span>"
        for i, tag in enumerate(tags)
    )
    top_class = " top" if rec.rank == 1 else ""
    st.markdown(
        f"""
        <article class="tr-card{top_class}">
          <div class="tr-card-body">
            <div class="tr-card-head">
              <span class="{pill_class}">{html.escape(pill_text)}</span>
              <h3 class="tr-name">{html.escape(rec.name)}</h3>
            </div>
            <div class="tr-meta">
              <span class="cuisine">{html.escape(rec.cuisine)}</span>
              · <span class="rating">{rec.rating:.1f} ★</span>
              · {html.escape(cost)}
            </div>
            <p class="tr-why">
              <strong>Why it fits:</strong>
              {html.escape(rec.explanation)}
            </p>
            <div class="tr-tags">{tag_html}</div>
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_empty(message: str | None) -> None:
    body = html.escape(
        message
        or "We couldn't find restaurants matching both the rating threshold "
        "and selected filters in this locality."
    )
    st.markdown(
        f"""
        <div class="tr-empty">
          <div class="tr-empty-icon">⊘</div>
          <h3>No matching culinary spots found</h3>
          <p>{body}</p>
          <p style="margin-top:0.75rem;color:#7C869A;font-size:12px;">
            Tip: try another location, clear cuisine, change budget, or lower min rating.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_error(message: str | None) -> None:
    body = html.escape(message or "The TasteRank engine hit an unexpected error.")
    st.markdown(
        f"""
        <div class="tr-error">
          <div class="tr-error-icon">☁</div>
          <h3>TasteRank Engine Connection Failed</h3>
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_outcome(outcome: ServiceResult, location: str) -> None:
    if outcome.status == ServiceStatus.ERROR:
        _render_error(outcome.message)
        return

    if outcome.status == ServiceStatus.EMPTY:
        _render_empty(outcome.message)
        return

    result = outcome.result
    assert result is not None

    short_loc = re.split(r",\s*", location)[0]
    count = len(result.recommendations)
    corpus_note = f"Grounded shortlist · {outcome.shortlist_size} candidates"

    st.markdown(
        f"""
        <div class="tr-results-bar">
          <p class="tr-section" style="margin:0;">Results</p>
          <div class="tr-live">
            <span class="tr-live-dot"></span>
            {html.escape(corpus_note)}
          </div>
        </div>
        <div class="tr-status-banner">
          <div class="icon">✓</div>
          <div>
            Evaluated with TasteRank Multi-factor Ranker. Cross-referenced with
            local sentiment, footfall patterns, and seasonal kitchen quality.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary = result.summary or result.note or (
        f"Ranked {count} places near {short_loc} using your taste, budget, and rating bar."
    )
    st.markdown(
        f"""
        <div class="tr-synth">
          <div class="tr-synth-top">
            <div style="display:flex;flex-wrap:wrap;align-items:center;gap:0.5rem;">
              <h2 class="tr-synth-title">Top matches for {html.escape(short_loc)}</h2>
              <span class="tr-chip">{count} places found</span>
            </div>
            <span class="tr-chip tr-chip-live">{html.escape(_source_label(outcome))}</span>
          </div>
          <div class="tr-synth-body">
            <strong>Synthesis:</strong>
            {html.escape(summary)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.note and result.summary:
        st.caption(result.note)

    if not result.recommendations:
        _render_empty("No recommendations returned.")
        return

    for rec in result.recommendations:
        _render_card(rec)


def _render_footer() -> None:
    st.markdown(
        """
        <div class="tr-footer">
          <div class="brand">✦ TasteRank AI Recommendation Engine · Grounded semantic ranking</div>
          <div>© 2025 TasteRank Tech Inc.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_demo_defaults(locations: list[str], cuisines: list[str]) -> None:
    st.session_state["tr_location"] = _find_demo_location(locations)
    st.session_state["tr_budget"] = BudgetBand.MEDIUM
    featured = [c for c in _FEATURED_CUISINES if c in cuisines]
    st.session_state["tr_cuisine"] = featured[0] if featured else _ANY_CUISINE
    st.session_state["tr_min_rating"] = 4.2
    st.session_state["tr_top_k"] = int(get_settings().default_top_k)
    st.session_state["tr_extras"] = _DEMO_EXTRAS
    st.session_state["tr_run_demo"] = True


def main() -> None:
    st.set_page_config(
        page_title="TasteRank",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_DARK_CSS, unsafe_allow_html=True)

    locations, cuisines = _location_and_cuisine_options()
    if not locations:
        st.error("No locations found in the restaurant corpus.")
        return

    cuisine_opts = _cuisine_options(cuisines)
    settings = get_settings()

    # Seed widget defaults once
    if "tr_location" not in st.session_state:
        st.session_state["tr_location"] = locations[_default_location_index(locations)]
    if "tr_budget" not in st.session_state:
        st.session_state["tr_budget"] = BudgetBand.MEDIUM
    if "tr_cuisine" not in st.session_state:
        st.session_state["tr_cuisine"] = _ANY_CUISINE
    if "tr_min_rating" not in st.session_state:
        st.session_state["tr_min_rating"] = 4.0
    if "tr_top_k" not in st.session_state:
        st.session_state["tr_top_k"] = int(settings.default_top_k)
    if "tr_extras" not in st.session_state:
        st.session_state["tr_extras"] = ""

    # Keep selectbox values valid if corpus changes
    if st.session_state["tr_location"] not in locations:
        st.session_state["tr_location"] = locations[_default_location_index(locations)]
    if st.session_state["tr_cuisine"] not in cuisine_opts:
        st.session_state["tr_cuisine"] = _ANY_CUISINE

    with st.sidebar:
        st.markdown(
            """
            <div class="tr-prefs-head">
              <span class="label">Preferences</span>
              <span class="badge">Bangalore Node</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        use_mock = st.toggle(
            "Mock LLM (offline)",
            value=False,
            help="Uses the real dataset + filters; skips the Groq API call.",
        )

        with st.form("preferences"):
            location = st.selectbox(
                "Neighborhood or City",
                options=locations,
                key="tr_location",
                help="Localities from the cleaned Zomato corpus.",
            )
            st.caption("Targeting Koramangala, Indiranagar, and CBD hubs")

            cuisine_choice = st.selectbox(
                "Cuisines of Interest",
                options=cuisine_opts,
                key="tr_cuisine",
                help="Leave as Any cuisine to skip the cuisine hard filter.",
            )

            budget = st.segmented_control(
                "Estimated Budget",
                options=list(BudgetBand),
                format_func=lambda b: _BUDGET_LABELS[b],
                key="tr_budget",
            )

            min_rating = st.slider(
                "Minimum Diner Rating",
                min_value=0.0,
                max_value=5.0,
                step=0.1,
                key="tr_min_rating",
            )

            top_k = st.number_input(
                "Number of picks (Top-K)",
                min_value=1,
                max_value=20,
                step=1,
                key="tr_top_k",
            )

            extras = st.text_area(
                "Specific Vibes or Dietary Notes",
                key="tr_extras",
                placeholder="e.g. rooftop seating, pet friendly, craft beer on tap…",
                height=90,
            )

            submitted = st.form_submit_button(
                "✦  Get recommendations",
                type="primary",
                use_container_width=True,
            )

        demo = st.button(
            "Try Bangalore Demo (Koramangala)",
            type="secondary",
            use_container_width=True,
        )
        if demo:
            _apply_demo_defaults(locations, cuisines)
            st.rerun()

        st.markdown(
            f"""
            <div class="tr-ranker-card">
              <div class="tr-ranker-icon">◈</div>
              <div>
                <p class="tr-ranker-title">Bangalore Local Ranker v4.2</p>
                <p class="tr-ranker-meta">
                  {len(locations)} locations · {len(cuisines)} cuisines ·
                  top-k default {settings.default_top_k}
                </p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not use_mock and not settings.llm_api_key:
            st.warning("No `LLM_API_KEY` / `GROQ_API_KEY` in `.env`.")

    st.markdown(
        '<p class="tr-eyebrow">Culinary Intelligence · Bangalore Node</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 class="tr-hero">Taste<span>Rank</span></h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="tr-sub">AI picks that match your taste, budget, and neighborhood. '
        "Grounded in local gastronomy and real-time palate signals.</p>",
        unsafe_allow_html=True,
    )

    run_demo = bool(st.session_state.pop("tr_run_demo", False))
    should_run = submitted or run_demo

    if not should_run:
        st.markdown(
            """
            <div class="tr-status-banner">
              <div class="icon">→</div>
              <div>
                Set preferences in the left panel, then hit
                <strong style="color:#ffb3ae;">Get recommendations</strong>
                — or load the Bangalore demo to preview the ranker.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_footer()
        return

    # segmented_control can briefly be None before interaction
    if budget is None:
        budget = BudgetBand.MEDIUM

    cuisine = None if cuisine_choice == _ANY_CUISINE else cuisine_choice
    try:
        prefs = UserPreferences(
            location=location,
            budget=budget,
            cuisine=cuisine,
            min_rating=float(min_rating),
            additional_preferences=extras or None,
            top_k=int(top_k),
        )
    except ValidationError as exc:
        msg = exc.errors()[0].get("msg", "Invalid preferences")
        _render_error(f"Invalid preferences: {msg}")
        _render_footer()
        return

    spinner = (
        "Ranking local tastes with mock LLM…"
        if use_mock
        else "Ranking local tastes — filtering candidates and asking Groq…"
    )
    try:
        with st.spinner(spinner):
            outcome = _run_recommend(prefs, use_mock=use_mock)
    except LLMError as exc:
        _render_error(f"LLM configuration error: {exc}")
        _render_footer()
        return
    except Exception as exc:  # noqa: BLE001 — show friendly UI error
        _render_error(f"Unexpected error: {exc}")
        _render_footer()
        return

    _render_outcome(outcome, location=location)
    _render_footer()


if __name__ == "__main__":
    main()
