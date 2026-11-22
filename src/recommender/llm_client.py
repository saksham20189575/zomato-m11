"""LLM provider client — Groq via OpenAI-compatible API (Phase 3)."""

from __future__ import annotations

import logging
import ssl
import time
from typing import Protocol, runtime_checkable

import httpx2
import truststore
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from recommender.config import Settings, get_settings
from recommender.prompts import PromptPayload

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM call fails after retries (or is misconfigured)."""


@runtime_checkable
class LLMClient(Protocol):
    """Thin chat-completion contract; mockable for offline tests."""

    def complete(self, prompt: PromptPayload) -> str:
        """Return raw model text (expected to be JSON)."""
        ...


class MockLLMClient:
    """Injectable mock that returns a fixed payload (no network)."""

    def __init__(self, response: str, *, fail: bool = False) -> None:
        self.response = response
        self.fail = fail
        self.calls: list[PromptPayload] = []

    def complete(self, prompt: PromptPayload) -> str:
        self.calls.append(prompt)
        if self.fail:
            raise LLMError("MockLLMClient forced failure")
        return self.response


def _build_http_client(timeout_seconds: float) -> httpx2.Client:
    """HTTP client using the OS trust store (macOS/corporate CAs).

    Python's default cert bundle often fails on macOS framework builds and
    TLS-intercepting proxies; ``truststore`` uses system roots like curl.
    """
    return httpx2.Client(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        timeout=timeout_seconds,
    )


class GroqLLMClient:
    """Chat completions against Groq's OpenAI-compatible endpoint."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: OpenAI | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if client is not None:
            self._client = client
            return

        api_key = (self.settings.llm_api_key or "").strip()
        if not api_key:
            raise LLMError(
                "Missing Groq API key. Set LLM_API_KEY or GROQ_API_KEY in the "
                "environment / .env (see .env.example)."
            )
        self._client = OpenAI(
            api_key=api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=0,  # we own retry / backoff below
            http_client=_build_http_client(self.settings.llm_timeout_seconds),
        )

    def complete(self, prompt: PromptPayload) -> str:
        """Call Groq with limited retries on timeout / 429 / 5xx."""
        attempts = self.settings.llm_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.settings.llm_model,
                    messages=prompt.as_messages(),
                    temperature=self.settings.llm_temperature,
                )
            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                last_error = exc
                self._backoff(attempt, attempts, exc)
                continue
            except APIStatusError as exc:
                last_error = exc
                if exc.status_code >= 500 or exc.status_code == 429:
                    self._backoff(attempt, attempts, exc)
                    continue
                raise LLMError(f"Groq API error ({exc.status_code}): {exc.message}") from exc
            except Exception as exc:  # noqa: BLE001 — surface as LLMError
                raise LLMError(f"Groq request failed: {exc}") from exc

            content = (response.choices[0].message.content or "").strip()
            if not content:
                raise LLMError("Groq returned an empty model response")
            return content

        raise LLMError(
            f"Groq request failed after {attempts} attempt(s): {last_error}"
        ) from last_error

    @staticmethod
    def _backoff(attempt: int, attempts: int, exc: Exception) -> None:
        if attempt >= attempts:
            return
        delay = min(2 ** (attempt - 1), 8)
        logger.warning(
            "LLM attempt %s/%s failed (%s); retrying in %ss",
            attempt,
            attempts,
            type(exc).__name__,
            delay,
        )
        time.sleep(delay)


def create_llm_client(settings: Settings | None = None) -> GroqLLMClient:
    """Factory for the live Groq client from settings."""
    return GroqLLMClient(settings=settings)
