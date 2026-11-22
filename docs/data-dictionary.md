# Data Dictionary — Zomato Dataset Mapping

Source: Hugging Face
[`ManikaSaini/zomato-restaurant-recommendation`](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
(~51.7k rows, Bangalore-focused Zomato listings).

## Column → canonical field

| Source column | Canonical field | Notes |
|---|---|---|
| *(derived)* | `id` | Stable SHA-1 prefix of `name\|location\|address` |
| `name` | `name` | Required; empty → **drop row** |
| `location` | `location` (locality) | Locality (e.g. `Koramangala 5th Block`), not city |
| `address` | contributes to `location` | Appends city token (`Bangalore` / `Bengaluru`) when present so city-level prefs match |
| `cuisines` | `cuisines: list[str]` | Split on `,` `/` `\|`; empty → **drop** |
| `rate` | `rating: float` | Parse `"4.1/5"`, `"3.8 /5"`; `NEW` / `-` / null → **drop** |
| `approx_cost(for two people)` | `cost: float \| None` | Strip commas / currency; failed parse → `null` |
| *(derived)* | `cost_band` | `low` / `medium` / `high` from ingest percentiles (see below) |
| `votes` | `votes: int` | Missing / non-numeric → `0` |
| `rest_type`, `dish_liked`, `online_order`, `book_table`, `listed_in(type)`, `listed_in(city)`, `url`, `address` | `raw` | Kept for LLM context; not hard-filtered in v1 |

Extra source columns are ignored or stashed in `raw` (DI-08).

## Location semantics (DI-21)

- Dataset `location` is a **locality** within Bangalore (~93 values).
- ~94% of `address` values contain `Bangalore`; a smaller share use `Bengaluru`.
- Canonical `location` is `"<locality>, <city>"` when a city token is found, else just the locality.
- Phase 2 filters should treat location as case-insensitive substring / contains against this field (city **or** locality).

## Cost / rating distributions

Use these when tuning Phase 2 budget thresholds.

**Source corpus (pre-drop):** ~51.7k rows. Cost P33/P66 on all parseable costs ≈ **300 / 550** (used at ingest for bands).

**Cleaned corpus (post-drop + dedupe):** ~9.3k restaurants (drops `NEW`/`-` ratings, empty name/location/cuisines; one row per name+location).

| Metric (cleaned) | Value |
|---|---|
| Rating scale | 0–5 (stored as `X/5` strings) |
| Rating mean / median | ~3.70 / 3.70 |
| Rating range | 1.8 – 4.9 |
| Cost mean / median | ~603 / 500 |
| Approx band mix | ~low 12.6k / medium 12.7k / high 16.1k / none ~0.2k |

### Cost band policy (assigned once at ingest)

| Band | Rule |
|---|---|
| `low` | `cost <= P33` (inclusive) |
| `medium` | `P33 < cost <= P66` (inclusive upper) |
| `high` | `cost > P66` |
| *(none)* | `cost` is null / unparseable — excluded from budget hard-filter later |

If P33 ≈ P66 (degenerate distribution), fall back to configured
`BUDGET_LOW_MAX` / `BUDGET_MEDIUM_MAX` (defaults 300 / 550).

## Drop vs keep rules

| Condition | Action |
|---|---|
| Empty / null `name` | Drop |
| Empty / null locality | Drop |
| Unparseable rating (`NEW`, `-`, null) | Drop |
| Empty cuisines | Drop |
| Unparseable / null cost | Keep; `cost=None`, `cost_band=None` |
| Duplicate name+location (multi `listed_in(type)`) | **Dedupe**: keep highest rating, then votes; ids include url + listing type before dedupe |

## Cache

Cleaned corpus is written to `{CACHE_DIR}/restaurants.parquet`.
Delete that file to force a re-download / rebuild.
On corrupt cache, the loader rebuilds from the Hugging Face source (or raises a clear error if that fails).
