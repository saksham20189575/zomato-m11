"""Start the TasteRank API.

Railway injects PORT as an environment variable. Do not pass ``$PORT`` on the
uvicorn CLI — Railway does not expand that, and a variable whose value is the
text ``$PORT`` is not a port number.
"""

from __future__ import annotations

import os

import uvicorn


def resolve_port() -> int:
    raw = os.environ.get("PORT", "").strip()
    if raw.isdigit():
        return int(raw)
    if raw:
        print(
            f"Ignoring non-numeric PORT={raw!r}. "
            "Delete the PORT variable in Railway so the platform can set it. Using 8000."
        )
    return 8000


def main() -> None:
    uvicorn.run("app.api:app", host="0.0.0.0", port=resolve_port())


if __name__ == "__main__":
    main()
