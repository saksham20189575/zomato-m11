"""Smoke tests for Phase 0 config loading."""

from __future__ import annotations

from recommender.config import (
    DEFAULT_GROQ_BASE_URL,
    DEFAULT_GROQ_MODEL,
    Settings,
    get_settings,
)


def test_get_settings_defaults() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.dataset_name
    assert settings.max_candidates >= 1
    assert settings.default_top_k >= 1


def test_groq_defaults_when_env_unset(monkeypatch) -> None:
    for key in (
        "LLM_API_KEY",
        "GROQ_API_KEY",
        "LLM_MODEL",
        "LLM_BASE_URL",
        "LLM_TEMPERATURE",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None)
    assert settings.llm_model == DEFAULT_GROQ_MODEL
    assert settings.llm_base_url == DEFAULT_GROQ_BASE_URL
    assert settings.llm_temperature == 0.2
