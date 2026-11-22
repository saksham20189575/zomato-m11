# TasteRank FastAPI — Railway / container deploy
# Mount a volume at /data and set CACHE_DIR=/data to persist the HF cache.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY app ./app
COPY scripts/start_api.sh ./scripts/start_api.sh

RUN pip install --no-cache-dir -e ".[api]" \
    && chmod +x scripts/start_api.sh

ENV CACHE_DIR=/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Shell script expands PORT; avoids literal "$PORT" when the platform skips shell expansion.
CMD ["sh", "scripts/start_api.sh"]
