#!/bin/sh
# Prefer scripts/serve.py — it reads PORT from the environment.
set -e
exec python scripts/serve.py
