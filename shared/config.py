"""Runtime configuration helpers.

This module intentionally keeps configuration access simple and explicit:
- environment is loaded from `.env` when available
- keys are fetched at call time to avoid stale values in long-lived sessions
- helper methods never print or return masked variants to logs
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings from environment variables."""

    groq_api_key: str | None
    openrouter_api_key: str | None


def _read_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_settings() -> Settings:
    """Read settings from current process environment."""
    return Settings(
        groq_api_key=_read_env("GROQ_API_KEY"),
        openrouter_api_key=_read_env("OPENROUTER_API_KEY"),
    )


def has_groq_api_key() -> bool:
    return get_settings().groq_api_key is not None


def has_openrouter_api_key() -> bool:
    return get_settings().openrouter_api_key is not None


def require_api_key(provider: str) -> str:
    """Return configured API key for a provider or raise ValueError."""
    normalized = provider.strip().lower()
    settings = get_settings()

    if normalized == "groq":
        key = settings.groq_api_key
    elif normalized == "openrouter":
        key = settings.openrouter_api_key
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    if key is None:
        raise ValueError(f"Missing API key for provider: {normalized}")
    return key
