# Architecture — AI-Powered Restaurant Recommendation System

## Purpose

This document defines the detailed architecture for `zomato-m11`: components, data flow, contracts, and design decisions for an AI-powered restaurant recommendation service inspired by Zomato.

It complements [`problemStatement.md`](./problemStatement.md), which owns product goals and scope. This file owns **how** the system is structured and how pieces interact.

---

## Design Principles

1. **Grounded recommendations** — The LLM ranks and explains only restaurants that already passed structured filters; it must not invent venues.
2. **Filter first, reason second** — Deterministic filtering shrinks the candidate set; the LLM handles ranking, nuance, and explanation.
3. **Clear separation of concerns** — Ingestion, filtering, prompting, LLM client, and presentation stay in distinct modules.
4. **Explainability** — Every recommendation includes a human-readable reason tied to user preferences and restaurant attributes.
5. **Prototype-first** — Prefer a simple, readable stack suitable for learning; defer production concerns (auth, scale, booking) unless added later.

---

## System Context

```text
┌─────────────┐     preferences      ┌──────────────────────────────────────┐
│    User     │ ───────────────────► │  Restaurant Recommendation App      │
│  (CLI/UI)   │ ◄─────────────────── │                                      │
└─────────────┘   ranked results     │  • Preference capture                │
                                     │  • Dataset filtering                 │
┌─────────────┐                      │  • LLM ranking + explanations        │
│ Hugging Face│ ◄── load once /      │  • Result formatting                 │
│  Dataset    │     cache locally    └───────────────┬──────────────────────┘
└─────────────┘                                      │
                                                     │ prompt + candidates
                                                     ▼
                                           ┌─────────────────┐
                                           │  LLM Provider   │
                                           │  (API / local)  │
                                           └─────────────────┘
```

**External dependencies**

| Dependency | Role |
|---|---|
| Hugging Face dataset `ManikaSaini/zomato-restaurant-recommendation` | Source of restaurant records |
| LLM provider — **Groq** (OpenAI-compatible API at `https://api.groq.com/openai/v1`) | Ranking, explanations, optional summary |
| Optional: local cache / parquet / CSV export | Avoid re-downloading the dataset on every run |

---

## Logical Architecture

The system is organized into five layers.

```text
┌─────────────────────────────────────────────────────────────┐
│  Presentation Layer                                         │
│  CLI / Notebook / Web UI — collect prefs, show results      │
└────────────────────────────┬────────────────────────────────┘
                             │ UserPreferences DTO
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Application / Orchestration Layer                          │
│  RecommendationService — end-to-end use-case flow           │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐
│ Data Layer   │  │ Filter Layer │  │ Recommendation Engine   │
│ Ingestion +  │  │ Candidate    │  │ Prompt Builder + LLM    │
│ Repository   │  │ Selector     │  │ Client + Response Parse │
└──────────────┘  └──────────────┘  └─────────────────────────┘
```

---

## Component Breakdown

### 1. Presentation Layer

**Responsibility:** Collect user preferences and render recommendations.

**Inputs from user**

| Field | Type | Required | Description |
|---|---|---|---|
| `location` | string | yes | City / area (e.g. Bangalore) |
| `budget` | enum: `low` \| `medium` \| `high` | yes | Maps to cost bands |
| `cuisine` | string | yes | Preferred cuisine |
| `min_rating` | float | yes | Minimum acceptable rating |
| `additional_preferences` | string (optional) | no | Free-text (e.g. family-friendly) |
| `top_k` | int (optional) | no | Number of results to return (default 5) |

**Outputs to user**

For each recommendation:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation

Optionally: short overall summary of the recommendation set.

**Implementation options**

- CLI (simplest for prototype)
- Jupyter / Streamlit app (optional demo UI)
- **Primary web UI:** FastAPI JSON API (`app/api.py`) + Next.js TasteRank frontend (`web/`), ported from the Stitch dark design system

### 2. Application / Orchestration Layer

**Component:** `RecommendationService`

**Responsibility:** Wire the full use case without embedding filter or LLM logic.

**Flow**

1. Validate `UserPreferences`
2. Load restaurant corpus via `RestaurantRepository`
3. Apply `CandidateFilter` → shortlist
4. If shortlist is empty → return empty/friendly message (no LLM call)
5. Build prompt via `PromptBuilder`
6. Call `LLMClient`
7. Parse / validate response into `RecommendationResult`
8. Pass results to presentation

**Why this layer exists:** Keeps UI thin and makes the pipeline testable in isolation.

### 3. Data Layer

#### 3.1 Data Ingestion

**Component:** `DatasetLoader`

- Fetch Hugging Face dataset `ManikaSaini/zomato-restaurant-recommendation`
- Select and normalize columns into a common restaurant schema
- Handle missing / noisy values (empty cuisine, non-numeric ratings, odd cost strings)
- Optionally persist a cleaned local snapshot (CSV/Parquet) for faster reloads

#### 3.2 Restaurant Repository

**Component:** `RestaurantRepository`

- Provide query interface over the cleaned corpus
- Hide storage details (in-memory DataFrame, SQLite, etc.) from upper layers

**Canonical restaurant record (internal model)**

| Field | Description |
|---|---|
| `id` | Stable identifier (dataset index or hash) |
| `name` | Restaurant name |
| `location` | City / locality |
| `cuisines` | List or delimited string of cuisines |
| `cost` | Numeric average cost (or normalized band) |
| `cost_band` | Derived: `low` / `medium` / `high` |
| `rating` | Numeric rating |
| `votes` | Optional popularity signal |
| `raw` | Optional bag of leftover attributes for LLM context |

### 4. Filter Layer (Integration)

**Component:** `CandidateFilter`

**Responsibility:** Deterministically reduce the corpus to a manageable, preference-aligned shortlist **before** LLM reasoning.

**Typical filter pipeline**

```text
Full corpus
  → location match (exact / contains / normalized)
  → cuisine match (substring / token overlap)
  → min_rating threshold
  → budget / cost_band match
  → optional soft re-rank by rating / votes
  → truncate to N candidates (e.g. 10–30) for the LLM context window
```

**Budget mapping (example policy — tune to dataset distributions)**

| Budget | Example cost rule |
|---|---|
| `low` | cost ≤ P33 of dataset (or fixed threshold) |
| `medium` | P33 < cost ≤ P66 |
| `high` | cost > P66 |

**Hard vs soft rules**

- **Hard filters:** location, min_rating, cuisine (must match to enter shortlist)
- **Soft signals:** votes, exact locality closeness, additional free-text prefs (handled by LLM)

**Empty shortlist strategy**

1. Relax cuisine match, then budget, then rating (configurable order), **or**
2. Return no results with a clear message asking the user to broaden prefs

Prefer explicit behavior over silent over-relaxation unless configured.

### 5. Recommendation Engine

#### 5.1 Prompt Builder

**Component:** `PromptBuilder`

Builds a structured prompt containing:

- User preferences (including free-text extras)
- Candidate restaurant list as structured JSON / bullet records
- Instructions: rank, explain, stay within candidates only, return fixed JSON schema

**Prompt contract goals**

- No restaurants outside the candidate list
- Stable machine-parseable output
- Explanations reference concrete attributes (cuisine, cost, rating, extras)

#### 5.2 LLM Client

**Component:** `LLMClient`

- Send prompt to configured provider
- Configure temperature (low–moderate for ranking consistency)
- Handle timeouts, rate limits, and basic retries
- Return raw text for parsing

#### 5.3 Response Parser

**Component:** `ResponseParser`

- Parse LLM output into `RecommendationResult`
- Validate that every recommended `id` / name exists in the candidate set
- Drop or flag hallucinated entries
- Normalize fields for the UI

**Recommended LLM response schema**

```json
{
  "summary": "Optional one-paragraph overview",
  "recommendations": [
    {
      "restaurant_id": "123",
      "name": "Example Cafe",
      "rank": 1,
      "cuisine": "Italian",
      "rating": 4.3,
      "estimated_cost": 800,
      "explanation": "Matches Italian + medium budget with strong ratings."
    }
  ]
}
```

---

## End-to-End Data Flow

```text
[User] submits preferences
        │
        ▼
[RecommendationService] validates input
        │
        ▼
[RestaurantRepository] loads cleaned restaurants
        │
        ▼
[CandidateFilter] applies location / cuisine / rating / budget
        │
        ├── (0 candidates) → friendly empty result → [UI]
        │
        ▼
[PromptBuilder] creates grounded prompt
        │
        ▼
[LLMClient] returns ranked recommendations + explanations
        │
        ▼
[ResponseParser] validates IDs against candidates
        │
        ▼
[Presentation] displays top-K results
```

---

## Suggested Project Structure

```text
zomato-m11/
├── docs/
│   ├── problemStatement.md
│   ├── problemStatement.txt
│   └── architecture.md
├── data/                      # optional local cache of cleaned dataset
├── src/
│   └── recommender/
│       ├── __init__.py
│       ├── models.py          # UserPreferences, Restaurant, Recommendation
│       ├── ingestion.py       # DatasetLoader
│       ├── repository.py      # RestaurantRepository
│       ├── filters.py         # CandidateFilter
│       ├── prompts.py         # PromptBuilder
│       ├── llm_client.py      # GroqLLMClient + MockLLMClient
│       ├── parser.py          # ResponseParser + fallback helper
│       ├── engine.py          # RecommendationEngine (prompt→LLM→parse)
│       ├── service.py         # RecommendationService
│       └── config.py          # env, paths, Groq model, thresholds
├── app/
│   └── main.py                # CLI or web entrypoint
├── tests/
│   ├── test_filters.py
│   ├── test_parser.py
│   ├── test_prompts.py
│   ├── test_llm_client.py
│   ├── test_engine.py
│   └── test_service.py
├── requirements.txt / pyproject.toml
└── README.md
```

Language assumption for this prototype: **Python**, given Hugging Face datasets + common LLM SDKs. Swap packaging if another stack is chosen, but keep the same component boundaries.

---

## Configuration

Centralize runtime config (env vars / config file):

| Key | Purpose |
|---|---|
| `DATASET_NAME` / local path | Hugging Face id or cached file |
| `LLM_API_KEY` | Provider credential |
| `LLM_MODEL` | Model name |
| `LLM_BASE_URL` | Optional custom endpoint |
| `MAX_CANDIDATES` | Max restaurants sent to the LLM |
| `DEFAULT_TOP_K` | Default number of shown recommendations |
| `BUDGET_THRESHOLDS` | Cost cutoffs for low/medium/high |
| `CACHE_DIR` | Local cleaned dataset cache |

Never commit secrets; load keys from environment or a local `.env` (gitignored).

---

## Error Handling & Resilience

| Scenario | Behavior |
|---|---|
| Dataset download failure | Clear error; suggest using local cache if available |
| Invalid user input | Validation errors before any LLM call |
| Empty shortlist | No LLM call; actionable message |
| LLM timeout / API error | Retry with backoff; then fail gracefully |
| Malformed LLM JSON | Repair attempt or fallback to heuristic rank of filtered candidates |
| Hallucinated restaurant | Drop during parse; log warning |

---

## Non-Functional Considerations

| Concern | Approach for v1 |
|---|---|
| Latency | Cache dataset; keep candidate count small; one LLM call per request |
| Cost | Truncate candidates; concise prompts; avoid multi-turn chat unless needed |
| Reliability | Validate LLM output against candidates |
| Observability | Log preference → shortlist size → model → parse success |
| Privacy | No user accounts in v1; do not log secrets |

---

## Security Notes

- Treat LLM output as untrusted: parse and validate before display
- Do not put API keys in prompts, source control, or client-side code
- Sanitize any free-text preferences before embedding in prompts if later exposed via a public web form

---

## Testing Strategy

| Layer | What to test |
|---|---|
| Ingestion | Column mapping, null handling, cost/rating normalization |
| Filters | Location/cuisine/budget/rating combinations; empty results |
| Prompt builder | Candidate inclusion; instruction presence; schema hints |
| Parser | Valid JSON; rejection of unknown restaurants; ranking order |
| Service | Happy path + empty shortlist + LLM failure fallback |
| Smoke | One end-to-end run with mocked LLM |

Prefer unit tests with a tiny fixture dataset over live Hugging Face + live LLM in CI.

---

## Extension Points (Post-v1)

- Embeddings / semantic search for cuisine and free-text prefs
- User history and personalization
- Multi-city routing and map-based UI
- A/B testing of prompts
- Streaming responses for the UI
- Persistence of recommendation sessions

These are **not** required for the initial architecture to be complete.

---

## Architecture Decision Summary

| Decision | Choice | Rationale |
|---|---|---|
| Retrieval style | Structured filter → LLM rank | Grounded, cheaper, easier to debug than pure LLM over full corpus |
| LLM role | Rank + explain (not invent) | Reduces hallucination |
| Output format | Structured JSON from LLM | Reliable UI rendering |
| Data source | Hugging Face Zomato dataset | Matches problem statement |
| App shape | Service + thin UI | Clean boundaries for a learning prototype |

---

## Traceability to Problem Statement

| Problem statement stage | Architecture component(s) |
|---|---|
| Data Ingestion | `DatasetLoader`, `RestaurantRepository` |
| User Input | Presentation layer + `UserPreferences` |
| Integration Layer | `CandidateFilter`, `PromptBuilder` |
| Recommendation Engine | `LLMClient`, `ResponseParser` |
| Output Display | Presentation layer |

---

## Status

- **Architecture status:** Design baseline for implementation
- **Code status:** Not yet implemented (docs-only repository at time of writing)
