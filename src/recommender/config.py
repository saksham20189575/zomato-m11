"""Runtime configuration loaded from environment / `.env`."""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: src/recommender/config.py → parents[2]
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Groq OpenAI-compatible endpoint (https://console.groq.com/docs/openai)
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# Fast/cheap production model on Groq free+developer tiers (post Llama deprecation).
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


class Settings(BaseSettings):
    """Central config for dataset, LLM, and recommendation thresholds."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    dataset_name: str = Field(
        default="ManikaSaini/zomato-restaurant-recommendation",
        alias="DATASET_NAME",
        description="Hugging Face dataset id or local path",
    )
    cache_dir: Path = Field(
        default=_PROJECT_ROOT / "data",
        alias="CACHE_DIR",
        description="Local directory for cleaned dataset cache",
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "GROQ_API_KEY"),
        description="Groq API key (never commit); GROQ_API_KEY also accepted",
    )
    llm_model: str = Field(
        default=DEFAULT_GROQ_MODEL,
        alias="LLM_MODEL",
        description="Groq chat model id",
    )
    llm_base_url: str = Field(
        default=DEFAULT_GROQ_BASE_URL,
        alias="LLM_BASE_URL",
        description="OpenAI-compatible base URL (defaults to Groq)",
    )
    llm_temperature: float = Field(
        default=0.2,
        alias="LLM_TEMPERATURE",
        ge=0.0,
        le=2.0,
        description="Low–moderate temperature for stabler ranking",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        alias="LLM_TIMEOUT_SECONDS",
        gt=0.0,
        description="Per-request HTTP timeout for the LLM client",
    )
    llm_max_retries: int = Field(
        default=2,
        alias="LLM_MAX_RETRIES",
        ge=0,
        description="Retries on timeout / 429 / 5xx before failing",
    )
    max_candidates: int = Field(
        default=20,
        alias="MAX_CANDIDATES",
        description="Max restaurants sent to the LLM",
        ge=1,
    )
    default_top_k: int = Field(
        default=5,
        alias="DEFAULT_TOP_K",
        description="Default number of recommendations to return",
        ge=1,
    )
    # Cost cutoffs (absolute); Phase 1 may replace with percentile-based bands
    budget_low_max: float = Field(
        default=300.0,
        alias="BUDGET_LOW_MAX",
        description="Max cost for low budget band",
    )
    budget_medium_max: float = Field(
        default=550.0,
        alias="BUDGET_MEDIUM_MAX",
        description="Max cost for medium budget band (fallback ≈ dataset P66)",
    )


def get_settings() -> Settings:
    """Load settings from environment and optional `.env` file."""
    return Settings()
