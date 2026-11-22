# zomato-m11

AI-powered restaurant recommendation system inspired by Zomato.

See [`docs/problemStatement.md`](docs/problemStatement.md) for goals and
[`docs/architecture.md`](docs/architecture.md) for component design.
Implementation follows [`docs/implementation-plan.md`](docs/implementation-plan.md).

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,ui]"  # omit ,ui if you only need the CLI
cp .env.example .env        # then edit secrets locally (never commit .env)
```

## Configuration

Copy `.env.example` to `.env` and set values as needed.

**LLM provider:** [Groq](https://console.groq.com/) via the OpenAI-compatible
API (`LLM_BASE_URL=https://api.groq.com/openai/v1`). Create a key at
https://console.groq.com/keys and set `LLM_API_KEY` (or `GROQ_API_KEY`).

| Variable | Purpose |
|---|---|
| `DATASET_NAME` | Hugging Face dataset id |
| `CACHE_DIR` | Local cleaned-dataset cache |
| `LLM_API_KEY` / `GROQ_API_KEY` | Groq API key (required for live LLM) |
| `LLM_MODEL` | Groq model id (default `openai/gpt-oss-20b`) |
| `LLM_BASE_URL` | OpenAI-compatible base URL (defaults to Groq) |
| `LLM_TEMPERATURE` | Chat temperature (default `0.2`) |
| `LLM_TIMEOUT_SECONDS` | Per-request timeout |
| `LLM_MAX_RETRIES` | Retries on timeout / 429 / 5xx |
| `MAX_CANDIDATES` | Max restaurants sent to the LLM |
| `DEFAULT_TOP_K` | Default number of recommendations |

API keys must stay in `.env` (gitignored) or the environment — never in source.

For a stronger (slower) model, set `LLM_MODEL=openai/gpt-oss-120b`.

## Run (Phase 4 CLI)

Interactive (prompts for preferences):

```bash
python -m app.main
# or, after install:
zomato-recommend
```

Non-interactive flags:

```bash
python -m app.main \
  --location Bangalore \
  --budget medium \
  --cuisine Chinese \
  --min-rating 4.0 \
  --extras "family-friendly" \
  --top-k 3
```

Offline demo (no Groq call; still uses the real dataset/cache):

```bash
python -m app.main --mock \
  --location Bangalore --budget medium --cuisine Chinese --min-rating 4.0 --top-k 3
```

Example output shape:

```text
============================================================
Restaurant Recommendations
============================================================
Prefs: Bangalore | medium | Chinese | min_rating>=4.0 | extras='family-friendly'
Shortlist: 20 | Model: openai/gpt-oss-20b | Source: Groq LLM

Summary:
...

1. Wok Paper Scissors
   Asian, Malaysian, Chinese, ... | rating 4.3 | cost ~550
   Why: ...
```

Empty shortlists print a friendly tip and **do not** call the LLM. If Groq fails,
results fall back to rating-based ranking with a clear note.

## Run (TasteRank web — Next.js + FastAPI)

Primary web UI: Stitch-aligned **TasteRank** frontend (`web/`) talking to a thin
FastAPI layer over the same `RecommendationService`. API keys stay in `.env`
on the server — never exposed to the browser.

```bash
# Terminal 1 — API
pip install -e ".[api]"
uvicorn app.api:app --reload --port 8000

# Terminal 2 — Next.js
cd web
cp .env.local.example .env.local   # if needed; defaults to localhost:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use **Mock LLM (offline)**
in Preferences for a demo without calling Groq, or **Try Bangalore Demo**.

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /meta` | Locations + cuisines |
| `POST /recommend` | Ranked recommendations (`UserPreferences` + optional `mock`) |

Set `CORS_ORIGINS` (comma-separated) when the UI is not on localhost — see `.env.example`.

## Deploy (Vercel + Railway)

Free production path: **Vercel** (`web/`) + **Railway** (FastAPI). Step-by-step:
[`docs/deployment-plan.md`](docs/deployment-plan.md).

Backend artifacts: `Dockerfile`, `railway.toml`, `Procfile`, `requirements.txt`.

## Run (Phase 6 Streamlit UI)

Optional Streamlit UI over the same service (kept for quick demos):

```bash
pip install -e ".[ui]"   # if not already installed with ui extra
streamlit run app/streamlit_app.py
```

The CLI path above is unchanged.

### Preview cleaned dataset (Phase 1)

```bash
python scripts/preview_dataset.py
```

Loads the Hugging Face corpus (or local `DATASET_NAME` path), writes
`data/restaurants.parquet`, and prints corpus size, 3 samples, and
cost/rating distribution notes. Column mapping:
[`docs/data-dictionary.md`](docs/data-dictionary.md).

### Preview candidate filter (Phase 2)

```bash
python scripts/preview_filter.py
```

Prints a deterministic shortlist for a sample Bangalore + Chinese + medium
budget query (no LLM). Empty shortlists include an explicit reason message.

### LLM recommendation engine (Phase 3)

Phase 3 adds grounded ranking + explanations:

- `PromptBuilder` — preferences + compact candidate JSON
- `GroqLLMClient` — Groq chat completions (OpenAI SDK)
- `MockLLMClient` — offline / tests
- `ResponseParser` — drops hallucinated ids; prefers dataset fields
- `RecommendationEngine` — LLM path with heuristic fallback

Golden prompt example: [`docs/examples/golden-prompt.md`](docs/examples/golden-prompt.md).

Offline (mocked) smoke:

```bash
python scripts/preview_llm_engine.py
```

Live Groq (requires `LLM_API_KEY` in `.env`):

```bash
python scripts/preview_llm_engine.py --live
```

## Tests

```bash
pytest
```

Offline tests use `tests/fixtures/restaurants_raw.csv` and `MockLLMClient`
(no network / Groq key required).

## Project layout

```text
src/recommender/   # core package (models, ingestion, filters, LLM, service)
app/               # CLI (`main.py`) + FastAPI (`api.py`) + Streamlit (`streamlit_app.py`)
web/               # Next.js TasteRank UI (App Router + Tailwind)
tests/             # pytest suite
data/              # local dataset cache (gitignored contents)
docs/              # product + architecture + plan
```
