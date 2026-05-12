import json
import logging

import pytest

from shared.config import (
    _read_env,
    get_settings,
    has_groq_api_key,
    has_openrouter_api_key,
    require_api_key,
)
from shared.logging_utils import _sanitize
from shared.schemas import LLMRecommendation, NewsSentiment


def test_read_env_trims_and_normalizes_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "  abc123  ")
    monkeypatch.setenv("OPENROUTER_API_KEY", "   ")

    assert _read_env("GROQ_API_KEY") == "abc123"
    assert _read_env("OPENROUTER_API_KEY") is None


def test_settings_and_presence_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "key1")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    settings = get_settings()
    assert settings.groq_api_key == "key1"
    assert settings.openrouter_api_key is None
    assert has_groq_api_key() is True
    assert has_openrouter_api_key() is False


def test_require_api_key_and_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    assert require_api_key("groq") == "groq-key"

    with pytest.raises(ValueError, match="Missing API key"):
        require_api_key("openrouter")

    with pytest.raises(ValueError, match="Unsupported provider"):
        require_api_key("anthropic")


def test_sanitize_redacts_known_secret_keys() -> None:
    payload = {
        "api_key": "secret",
        "Authorization": "Bearer token",
        "safe": "value",
    }

    out = _sanitize(payload)
    assert out["api_key"] == "***REDACTED***"
    assert out["Authorization"] == "***REDACTED***"
    assert out["safe"] == "value"


def test_pydantic_schema_validation_boundaries() -> None:
    good = NewsSentiment(
        headline="sample",
        sentiment="positive",
        confidence=0.7,
        brief_reason="Earnings beat expectations.",
    )
    assert good.confidence == 0.7

    with pytest.raises(Exception):
        NewsSentiment(
            headline="sample",
            sentiment="positive",
            confidence=1.2,
            brief_reason="Out of bounds confidence.",
        )

    rec = LLMRecommendation(
        recommendation="Hold",
        confidence=0.5,
        rationale="Mixed indicators.",
        key_risks=["macro uncertainty"],
    )
    assert json.loads(rec.model_dump_json())["recommendation"] == "Hold"
