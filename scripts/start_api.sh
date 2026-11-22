#!/bin/sh
# Expand PORT in-process so Railway/Docker never pass a literal "$PORT" to uvicorn.
set -e
PORT="${PORT:-8000}"
exec uvicorn app.api:app --host 0.0.0.0 --port "$PORT"
