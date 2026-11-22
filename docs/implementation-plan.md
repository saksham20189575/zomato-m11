# Implementation Plan — AI-Powered Restaurant Recommendation System

## Purpose

Phase-wise plan for building `zomato-m11` from docs to a working prototype. Follows [`problemStatement.md`](./problemStatement.md) for goals and [`architecture.md`](./architecture.md) for component boundaries.

Each phase has: goal, deliverables, tasks, acceptance criteria, and exit checklist. Do not start the next phase until the current exit checklist passes.

---

## Plan Overview

| Phase | Name | Outcome |
|---|---|---|
| 0 | Project bootstrap | Runnable Python package skeleton + config |
| 1 | Data ingestion & models | Cleaned restaurant corpus + typed models |
| 2 | Candidate filtering | Deterministic shortlist from user preferences |
| 3 | LLM recommendation engine | Ranked, explained recommendations from candidates |
| 4 | Orchestration & CLI | End-to-end `RecommendationService` + user-facing CLI |
| 5 | Hardening & polish | Tests, error handling, docs, demo readiness |
| 6 (optional) | UI / extensions | Streamlit/web UI or post-v1 features |

```text
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → [Phase 6]
 bootstrap   data      filter    LLM       E2E CLI    polish     optional
```

**Dependency rule:** Phases 0–5 are sequential. Phase 3 can use a mocked LLM until a real key is available, but Phase 4 exit requires at least one successful live (or fully mocked E2E) run.

---

## Phase 0 — Project Bootstrap

### Goal

Create a clean, installable project layout so later phases plug into known modules.

### Deliverables

- Package structure matching architecture (`src/recommender/`, `app/`, `tests/`, `data/`, `docs/`)
- Dependency management (`pyproject.toml` or `requirements.txt`)
- Config loading from environment (no secrets in git)
- Minimal README with setup instructions
- `.gitignore` (`.env`, `data/` cache, `__pycache__`, venv)

### Tasks

1. Initialize virtual environment and package layout
2. Add core dependencies (planned):
   - `datasets` (Hugging Face)
   - `pandas` (or equivalent) for filtering
   - LLM SDK (OpenAI-compatible or chosen provider)
   - `python-dotenv` / pydantic-settings for config
   - `pytest` for tests
3. Implement `config.py` stubs: dataset name, cache dir, model name, `MAX_CANDIDATES`, `DEFAULT_TOP_K`
4. Add empty module stubs: `models`, `ingestion`, `repository`, `filters`, `prompts`, `llm_client`, `parser`, `service`
5. Add `app/main.py` placeholder that prints “not implemented”
6. Verify `pip install -e .` (or equivalent) and `pytest` collect zero/empty suite cleanly

### Acceptance Criteria

- [ ] Project installs in a fresh venv
- [ ] Config reads from env / `.env.example` documented
- [ ] Module import paths match architecture doc
- [ ] No API keys committed

### Exit Checklist

- [ ] README has setup + how to run (even if app is stub)
- [ ] `.env.example` exists; `.env` is gitignored

**Estimated effort:** 0.5–1 day

---

## Phase 1 — Data Ingestion & Domain Models

### Goal

Load the Hugging Face Zomato dataset, normalize fields into a canonical restaurant model, and expose them via a repository.

### Deliverables

- `UserPreferences`, `Restaurant`, and related models in `models.py`
- `DatasetLoader` that fetches / caches the dataset
- Cleaned local cache under `data/` (optional but recommended)
- `RestaurantRepository` with `load()` / `all()` (or equivalent)
- Unit tests for normalization edge cases

### Tasks

1. Inspect dataset columns and document mapping in code comments or a short `docs/data-dictionary.md` note
2. Define pydantic/dataclass models:
   - `UserPreferences` (location, budget, cuisine, min_rating, additional_preferences, top_k)
   - `Restaurant` (id, name, location, cuisines, cost, cost_band, rating, votes, raw)
3. Implement ingestion:
   - Download dataset once; cache cleaned CSV/Parquet
   - Normalize location, cuisine strings, rating (numeric), cost (numeric)
   - Derive `cost_band` (`low` / `medium` / `high`) from thresholds or percentiles
4. Handle missing/noisy values with explicit rules (drop vs default)
5. Implement `RestaurantRepository` over in-memory DataFrame or list
6. Add a small fixture dataset (10–20 rows) for offline tests
7. Write tests: rating parse, cost parse, cuisine split, cache hit path

### Acceptance Criteria

- [ ] Loader can produce a non-empty list/DataFrame of `Restaurant` records
- [ ] Re-running uses cache when present (no mandatory re-download)
- [ ] Budget bands are assigned consistently
- [ ] Tests cover at least 3 normalization edge cases

### Exit Checklist

- [ ] Sample script or notebook cell prints dataset size + 3 sample restaurants
- [ ] Cost/rating distributions briefly noted (for tuning Phase 2 thresholds)

**Estimated effort:** 1–2 days

---

## Phase 2 — Candidate Filtering

### Goal

Given `UserPreferences`, return a deterministic shortlist of restaurants ready for the LLM.

### Deliverables

- `CandidateFilter` with composable hard filters
- Configurable `MAX_CANDIDATES` truncation (e.g. top by rating/votes)
- Empty-result behavior (clear message / empty list — no silent inventing)
- Unit tests for filter combinations

### Tasks

1. Implement filters:
   - Location match (case-insensitive contains / normalized)
   - Cuisine match (token / substring against cuisine list)
   - `min_rating` threshold
   - Budget / `cost_band` match
2. Soft pre-rank shortlist by rating (then votes) before truncation
3. Implement empty shortlist path (return `[]` + reason code or message)
4. Optional: configurable relaxation order (document; keep off by default)
5. Tests:
   - Happy path returns expected IDs from fixture
   - Rating too high → empty
   - Wrong city → empty
   - Cuisine mismatch → empty
   - Truncation respects `MAX_CANDIDATES`

### Acceptance Criteria

- [ ] Filter is pure/deterministic given same corpus + prefs
- [ ] Never returns restaurants outside hard-filter constraints
- [ ] Shortlist size ≤ `MAX_CANDIDATES`
- [ ] Empty shortlist is explicit and test-covered

### Exit Checklist

- [ ] Manual run: print shortlist for a sample Bangalore + cuisine + budget query
- [ ] Filter module has no LLM dependency

**Estimated effort:** 1 day

---

## Phase 3 — LLM Recommendation Engine

### Goal

Turn a candidate shortlist + preferences into ranked recommendations with explanations, validated against the candidate set.

### Deliverables

- `PromptBuilder` with grounded instructions + JSON schema
- `LLMClient` (real provider + injectable mock for tests)
- `ResponseParser` that rejects hallucinated restaurants
- Fallback strategy when LLM fails or returns bad JSON
- Unit tests with mocked LLM responses

### Tasks

1. Design prompt template:
   - System: rank only from candidates; output JSON only
   - User: preferences + candidate records (compact JSON)
2. Implement `LLMClient`:
   - Model/base URL/API key from config
   - Low–moderate temperature
   - Timeout + limited retries
3. Implement `ResponseParser`:
   - Parse JSON (with light repair if wrapped in markdown fences)
   - Validate `restaurant_id` / name ∈ candidates
   - Drop invalid rows; preserve rank order
4. Define `Recommendation` / `RecommendationResult` models (summary + list)
5. Fallback: if LLM fails, heuristic rank (rating) + template explanation (“Matched your filters; LLM unavailable”)
6. Tests:
   - Valid JSON → parsed results
   - Hallucinated ID dropped
   - Markdown-fenced JSON still parses
   - Client mock returns controlled payload

### Acceptance Criteria

- [ ] Parser never emits a restaurant not in the candidate list
- [ ] Each recommendation has name, cuisine, rating, cost, explanation
- [ ] Mocked path works without network
- [ ] Live path documented in README (optional for this phase exit if mock-complete)

### Exit Checklist

- [ ] One golden prompt example saved under `docs/examples/` or in tests
- [ ] Fallback path tested

**Estimated effort:** 1–2 days

---

## Phase 4 — Orchestration & User Interface (CLI)

### Goal

Wire the full pipeline into `RecommendationService` and expose a usable CLI.

### Deliverables

- `RecommendationService` end-to-end orchestration
- CLI (`app/main.py`) collecting preferences and printing results
- Graceful handling of empty shortlist and LLM errors
- Demo-ready happy path

### Tasks

1. Implement service flow per architecture:
   validate → load → filter → (empty?) → prompt → LLM → parse → return
2. Wire dependencies via simple constructors or a small factory (avoid heavy DI framework)
3. Build CLI:
   - Interactive prompts and/or argparse flags
   - Fields: location, budget, cuisine, min_rating, additional_preferences, top_k
4. Pretty-print results (table or structured bullets)
5. Log: shortlist size, model name, parse success (no secrets)
6. Smoke-test with real dataset + real or mocked LLM

### Acceptance Criteria

- [ ] User can run one command and get top-K recommendations
- [ ] Empty shortlist shows a helpful message (no crash, no LLM call)
- [ ] LLM failure uses fallback or clear error (no stack trace dump to user)
- [ ] Output includes AI explanation per restaurant

### Exit Checklist

- [ ] README updated with example command + sample output
- [ ] `.env.example` lists all required keys for live LLM

**Estimated effort:** 1 day

---

## Phase 5 — Hardening, Tests & Demo Polish

### Goal

Make the prototype reliable enough to demo and hand off.

### Deliverables

- Test suite covering filters, parser, service (mocked LLM)
- Improved error messages and validation
- Final README (setup, architecture link, demo script)
- Known limitations documented

### Tasks

1. Add/finish unit + service tests; aim for critical-path coverage (not vanity %)
2. Validate `UserPreferences` (budget enum, rating range, non-empty strings)
3. Harden dataset cache and offline fixture mode for demos without Hugging Face
4. Add a `Makefile` or scripts: `make test`, `make demo`
5. Record a short demo script (prefs → expected style of output)
6. Review docs trio for consistency (`problemStatement`, `architecture`, this plan)
7. Optional: basic logging levels (`INFO`/`DEBUG`)

### Acceptance Criteria

- [ ] `pytest` passes offline (mocked LLM + fixture data)
- [ ] Demo path runs in &lt; a few minutes after first data cache
- [ ] README is sufficient for a newcomer to run the app
- [ ] Known limitations / out-of-scope listed

### Exit Checklist

- [ ] v1 feature set from problem statement is met
- [ ] No secrets in repo
- [ ] Architecture components all have a corresponding implementation file

**Estimated effort:** 1 day

---

## Phase 6 (Optional) — UI & Extensions

### Goal

Improve UX or add post-v1 capabilities without changing core contracts.

### Option A — Streamlit / simple web UI

- Form for preferences
- Cards/table for recommendations + explanations
- Reuse `RecommendationService` unchanged

### Option B — Product extensions

- Embedding / semantic match for free-text prefs
- Prompt A/B variants
- Session history
- Multi-city UX / maps

### Acceptance Criteria (if pursued)

- [x] UI or extension calls the same service API
- [x] Core CLI path still works
- [x] New scope documented in problem statement or a changelog note

**Done (Option A):** `app/streamlit_app.py` — preference form + recommendation
cards; `pip install -e ".[ui]"` then `streamlit run app/streamlit_app.py`.
Mock toggle reuses `recommend_with_mock` from the service layer.

**Estimated effort:** 1–3 days depending on option

---

## Cross-Phase Definition of Done (v1)

The project is done for v1 when all of the following are true:

1. User preferences (location, budget, cuisine, min rating, optional extras) are collected
2. Real Zomato dataset is loaded and filtered
3. LLM ranks candidates and explains each pick (or documented fallback)
4. Results show name, cuisine, rating, cost, explanation
5. Recommendations are grounded in filtered candidates
6. Offline tests pass; README enables a demo run

---

## Suggested Timeline (Compressed)

| Week | Phases |
|---|---|
| Days 1–2 | Phase 0 + Phase 1 |
| Days 3–4 | Phase 2 + Phase 3 |
| Day 5 | Phase 4 |
| Day 6 | Phase 5 |
| Later | Phase 6 as needed |

Adjust if dataset quirks or LLM integration take longer; protect Phase 2 quality before investing in prompts.

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Messy/inconsistent dataset columns | Blocks Phase 1–2 | Inspect early; fixture + explicit normalization |
| LLM hallucinates restaurants | Bad UX / wrong results | Candidate IDs in prompt + parser validation |
| API cost / rate limits | Demo failures | Small `MAX_CANDIDATES`; mock mode; cache dataset |
| Empty shortlists for strict prefs | “App feels broken” | Clear messaging; optional documented relaxation |
| Provider API changes | Phase 3/4 breakage | Thin `LLMClient` wrapper; contract tests with mocks |

---

## Tracking Checklist (copy into issues / PR)

- [x] Phase 0 — Bootstrap
- [x] Phase 1 — Data & models
- [x] Phase 2 — Filters
- [x] Phase 3 — LLM engine (Groq)
- [x] Phase 4 — Service + CLI
- [ ] Phase 5 — Harden & demo
- [x] Phase 6 — Optional UI/extensions (Streamlit Option A)

---

## Related Docs

- [`problemStatement.md`](./problemStatement.md) — what to build
- [`architecture.md`](./architecture.md) — how components fit
- This file — in what order to build it