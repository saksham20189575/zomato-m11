"""Unit tests for MockLLMClient and GroqLLMClient wiring (no live network)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import APITimeoutError

from recommender.config import Settings
from recommender.llm_client import GroqLLMClient, LLMError, MockLLMClient
from recommender.prompts import PromptPayload


def _prompt() -> PromptPayload:
    return PromptPayload(system="sys", user="user")


def _settings(**overrides: object) -> Settings:
    data = {
        "llm_api_key": "test-key",
        "llm_model": "openai/gpt-oss-20b",
        "llm_base_url": "https://api.groq.com/openai/v1",
        "llm_temperature": 0.2,
        "llm_max_retries": 0,
        "llm_timeout_seconds": 30.0,
    }
    data.update(overrides)
    return Settings(**data)


def test_mock_returns_controlled_payload() -> None:
    client = MockLLMClient('{"recommendations": []}')
    assert client.complete(_prompt()) == '{"recommendations": []}'
    assert len(client.calls) == 1


def test_mock_can_fail() -> None:
    client = MockLLMClient("x", fail=True)
    with pytest.raises(LLMError, match="forced failure"):
        client.complete(_prompt())


def test_groq_requires_api_key() -> None:
    with pytest.raises(LLMError, match="Missing Groq API key"):
        GroqLLMClient(settings=_settings(llm_api_key=""))


def test_groq_complete_happy_path() -> None:
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))]
    )
    client = GroqLLMClient(settings=_settings(), client=mock_openai)
    assert client.complete(_prompt()) == '{"ok": true}'
    kwargs = mock_openai.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-oss-20b"
    assert kwargs["temperature"] == 0.2
    assert kwargs["messages"][0]["role"] == "system"


def test_groq_empty_response_errors() -> None:
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  "))]
    )
    client = GroqLLMClient(settings=_settings(), client=mock_openai)
    with pytest.raises(LLMError, match="empty"):
        client.complete(_prompt())


def test_groq_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("recommender.llm_client.time.sleep", lambda _s: None)
    mock_openai = MagicMock()
    timeout = APITimeoutError(request=MagicMock())
    mock_openai.chat.completions.create.side_effect = [
        timeout,
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"retry":1}'))]
        ),
    ]
    client = GroqLLMClient(
        settings=_settings(llm_max_retries=1),
        client=mock_openai,
    )
    assert client.complete(_prompt()) == '{"retry":1}'
    assert mock_openai.chat.completions.create.call_count == 2


def test_groq_retries_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("recommender.llm_client.time.sleep", lambda _s: None)
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.side_effect = APITimeoutError(
        request=MagicMock()
    )
    client = GroqLLMClient(
        settings=_settings(llm_max_retries=1),
        client=mock_openai,
    )
    with pytest.raises(LLMError, match="after 2 attempt"):
        client.complete(_prompt())
