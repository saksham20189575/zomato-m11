"""CORS origin parsing for FastAPI deploy config."""

from __future__ import annotations

from app.api import parse_cors_origins


def test_parse_cors_origins_default(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert parse_cors_origins() == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_parse_cors_origins_from_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:3000, https://tasterank.vercel.app ",
    )
    assert parse_cors_origins() == [
        "http://localhost:3000",
        "https://tasterank.vercel.app",
    ]


def test_parse_cors_origins_explicit_raw() -> None:
    assert parse_cors_origins("https://a.vercel.app,https://b.vercel.app") == [
        "https://a.vercel.app",
        "https://b.vercel.app",
    ]


def test_parse_cors_origins_ignores_empty_segments() -> None:
    assert parse_cors_origins("http://localhost:3000,, ,https://x.vercel.app") == [
        "http://localhost:3000",
        "https://x.vercel.app",
    ]
