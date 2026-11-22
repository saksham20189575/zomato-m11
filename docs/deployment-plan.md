# Deployment Plan — TasteRank (Vercel + Railway)

Free production deploy for the TasteRank web stack:

| Layer | Path | Host | Role |
|---|---|---|---|
| Frontend | `web/` (Next.js 15) | [Vercel](https://vercel.com) | UI; calls API via `NEXT_PUBLIC_API_URL` |
| Backend | `app/api.py` (FastAPI) | [Railway](https://railway.app) | Recommendations, dataset cache, Groq key |
| LLM | Groq (existing) | [console.groq.com](https://console.groq.com) | Chat completions; not hosting |

Streamlit (`app/streamlit_app.py`) and the CLI are **out of scope** for this plan.

---

## Architecture (deployed)

```text
Browser
  │  NEXT_PUBLIC_API_URL=https://<railway-app>.up.railway.app
  ▼
Vercel (web/)  ──CORS──►  Railway (uvicorn app.api:app)
                              │
                              ├─ Hugging Face dataset → CACHE_DIR/data
                              └─ Groq API (LLM_API_KEY)
```

API surface (unchanged):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness |
| `GET` | `/meta` | Locations + cuisines |
| `POST` | `/recommend` | Ranked recommendations |

---

## Prerequisites

1. GitHub repo with this project pushed (public or private).
2. Accounts: [Vercel](https://vercel.com/signup), [Railway](https://railway.app), [Groq](https://console.groq.com/keys).
3. Python **3.10–3.12** recommended for Railway (avoid 3.14 unless verified).
4. Node **18+** for the Next.js app (Vercel default is fine).

---

## Phase 0 — Pre-deploy code changes (required)

**Status: implemented in repo.** Summary of what landed:

| Item | Location |
|---|---|
| `CORS_ORIGINS` parsing | `app/api.py` (`parse_cors_origins`) |
| Env example | `.env.example` |
| Dockerfile + ignore | `Dockerfile`, `.dockerignore` |
| Railway config | `railway.toml` (Docker builder, `/health` check) |
| Procfile / deps | `Procfile`, `requirements.txt` |
| CORS unit tests | `tests/test_api_cors.py` |

### 0.1 CORS: allow the Vercel origin

`app/api.py` reads `CORS_ORIGINS` (comma-separated). Defaults:

```text
http://localhost:3000
http://127.0.0.1:3000
```

On Railway, set e.g.:

```text
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://<your-vercel-app>.vercel.app
```

### 0.2 Railway install / start artifacts

Both options are in-repo:

- **Dockerfile** (default via `railway.toml`) — `pip install -e ".[api]"`, `CACHE_DIR=/data`
- **Nixpacks fallback** — `requirements.txt` + `Procfile`

Mount a Railway volume at `/data` when using the image.

### 0.3 Bind host and `$PORT`

Start command (Dockerfile `CMD`, `Procfile`, and `railway.toml`):

```bash
uvicorn app.api:app --host 0.0.0.0 --port $PORT
```

### 0.4 Frontend env (no code change if URL is set)

`web/src/lib/api.ts` and `web/next.config.ts` already read `NEXT_PUBLIC_API_URL`. Set it in Vercel to the Railway public HTTPS URL (no trailing slash). See `web/.env.local.example`.

### 0.5 Commit and push

Commit Phase 0 changes to the branch you will deploy (e.g. `main`).

---

## Phase 1 — Deploy backend on Railway

**Order matters:** deploy API first so Vercel can point at a real URL.

### 1.1 Create project

1. Railway → **New Project** → **Deploy from GitHub repo**.
2. Select `zomato-m11`.
3. Set **Root Directory** to repo root (not `web/`).
4. If using a Dockerfile, Railway usually detects it; otherwise set build/start as below.

### 1.2 Build & start (Nixpacks / custom)

| Setting | Value |
|---|---|
| Build | `pip install -e ".[api]"` (or Dockerfile build) |
| Start | `uvicorn app.api:app --host 0.0.0.0 --port $PORT` |
| Watch paths | Prefer ignoring `web/` if configurable |

### 1.3 Environment variables (Railway)

Set from `.env.example` (never commit real keys):

| Variable | Required | Notes |
|---|---|---|
| `LLM_API_KEY` or `GROQ_API_KEY` | Yes (live LLM) | From Groq console |
| `LLM_MODEL` | Optional | Default `openai/gpt-oss-20b` |
| `LLM_BASE_URL` | Optional | Default Groq OpenAI-compatible URL |
| `DATASET_NAME` | Optional | Default Hugging Face id |
| `CACHE_DIR` | Recommended | e.g. `/data` if volume mounted; else `/tmp/tasterank-cache` |
| `CORS_ORIGINS` | Yes (after 0.1) | Include Vercel URL + localhost for local UI → prod API testing |
| `MAX_CANDIDATES` | Optional | Default `20` |
| `DEFAULT_TOP_K` | Optional | Default `5` |

Omit secrets from GitHub Actions logs and screenshots.

### 1.4 Persistent cache (strongly recommended)

First `/meta` or `/recommend` may download the Hugging Face dataset and write `restaurants.parquet`. On free Railway, ephemeral disk means **re-download on every new deploy / new filesystem**.

1. Add a Railway **Volume**.
2. Mount at `/data` (or your `CACHE_DIR`).
3. Set `CACHE_DIR=/data`.

### 1.5 Public URL

1. Railway service → **Settings** → **Networking** → **Generate Domain**.
2. Copy `https://<service>.up.railway.app` (no trailing slash).
3. Confirm: `GET https://<service>.up.railway.app/health` → `{"status":"ok"}`.

### 1.6 Cold start note

Free / hobby instances may sleep when idle. First request after sleep can take tens of seconds and may coincide with dataset load if cache was empty. Prefer Mock LLM in the UI while warming up.

---

## Phase 2 — Deploy frontend on Vercel

### 2.1 Import project

1. Vercel → **Add New** → **Project** → import the same GitHub repo.
2. Configure:

| Setting | Value |
|---|---|
| **Root Directory** | `web` |
| Framework | Next.js (auto) |
| Build Command | `next build` (default) |
| Output | default |
| Install Command | `npm install` (default) |

### 2.2 Environment variables (Vercel)

| Variable | Environment | Value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Production (and Preview if desired) | `https://<service>.up.railway.app` |

`NEXT_PUBLIC_*` is inlined at **build** time. After changing it, **redeploy** the frontend.

### 2.3 Deploy

1. Deploy Production.
2. Note the URL: `https://<project>.vercel.app`.
3. Update Railway `CORS_ORIGINS` to include that exact origin (scheme + host, no path).
4. Redeploy or restart the Railway service so CORS picks up the new env.

### 2.4 Optional: Preview deployments

For Vercel Preview URLs, either:

- Add each preview origin to `CORS_ORIGINS` (impractical), or
- Temporarily allow a pattern / shared staging origin, or
- Point Preview builds at a staging API with broader CORS for `*.vercel.app` only if you accept the tradeoff.

Production-only CORS is fine for v1.

---

## Phase 3 — Wire-up checklist

Do in this order:

1. Railway `/health` returns `ok`.
2. Railway `/meta` returns locations/cuisines (may be slow first time).
3. Vercel homepage loads TasteRank UI.
4. Browser Network tab: `GET .../meta` and `POST .../recommend` succeed (not CORS blocked).
5. UI **Mock LLM (offline)** returns ranked results without Groq.
6. Live mode with Groq key returns AI explanations; on Groq failure, API should still fall back per product behavior.
7. Confirm Groq key never appears in browser JS or Network request payloads (only on Railway).

---

## Phase 4 — Smoke tests (manual)

```bash
# Health
curl -sS https://<railway>/health

# Meta
curl -sS https://<railway>/meta | head

# Mock recommend
curl -sS -X POST https://<railway>/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Koramangala, Bangalore",
    "budget": "medium",
    "cuisine": "Chinese",
    "min_rating": 4.0,
    "top_k": 3,
    "mock": true
  }'
```

Then in the Vercel UI: **Try Bangalore Demo** + Mock, then live.

---

## Free-tier limits & risks

| Risk | Mitigation |
|---|---|
| Railway sleep / cold start | Volume for cache; Mock path for demos; hit `/health` before presenting |
| Hugging Face download on empty cache | Mount volume at `CACHE_DIR`; keep service warm when demoing |
| Memory (pandas + datasets) | Prefer Python 3.12 slim; avoid loading unused extras; watch Railway metrics |
| Groq rate limits | Use Mock for load tests; keep `LLM_MAX_RETRIES` modest |
| CORS mismatch after renaming Vercel project | Update `CORS_ORIGINS` + restart API |
| `NEXT_PUBLIC_API_URL` stale | Redeploy Vercel after API URL changes |
| Secrets in client | Never put `LLM_API_KEY` in Vercel |

---

## Rollback

| Layer | Action |
|---|---|
| Vercel | Redeploy previous deployment from Deployments tab |
| Railway | Redeploy previous successful deployment; or unset bad env and restart |
| LLM | Set UI to Mock, or remove/rotate `LLM_API_KEY` on Railway |

---

## Optional follow-ups (not required for first deploy)

- Add `Dockerfile` + Railway volume as the default backend path.
- Health check path in Railway: `/health`.
- Custom domains on both Vercel and Railway; update CORS and `NEXT_PUBLIC_API_URL`.
- CI: run `pytest` on push before Railway deploy.
- Document Streamlit Community Cloud as an alternate single-service demo (separate from this plan).

---

## Acceptance criteria

- [ ] Backend publicly reachable over HTTPS with `/health` → `ok`
- [ ] Dataset loads successfully at least once; subsequent `/meta` is reasonably fast with volume
- [ ] Frontend on Vercel loads and talks to Railway without CORS errors
- [ ] Mock recommendations work without a Groq key
- [ ] Live recommendations work with `LLM_API_KEY` set only on Railway
- [ ] No secrets committed; `.env` / `.env.local` remain gitignored

---

## Suggested execution order (summary)

```text
1. Code: CORS_ORIGINS + Railway start/install (Phase 0) → push
2. Railway: deploy API → set env + volume → generate domain → /health
3. Vercel: root = web → NEXT_PUBLIC_API_URL → deploy
4. Railway: add Vercel origin to CORS_ORIGINS → restart
5. Smoke: mock + live from the Vercel UI
```

When Phase 0 is implemented and you are ready, deploy Railway first, then Vercel, then lock CORS to the real frontend URL.
