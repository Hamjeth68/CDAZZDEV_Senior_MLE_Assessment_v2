"""Runtime configuration helpers for LLM-backed assessment tasks.

Configuration is resolved from environment variables, with optional `.env`
loading for local development. Secrets are read only on demand and are never
hardcoded in this repository.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final, Literal

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

ProviderName = Literal["groq", "openrouter"]

PROVIDER_ENV_VARS: Final[dict[str, str]] = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings from environment variables."""

    groq_api_key: str | None
    openrouter_api_key: str | None


def _read_env(name: str) -> str | None:
    """Read and normalize an environment variable.

    Empty strings and whitespace-only values are treated as unset.
    """
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in PROVIDER_ENV_VARS:
        supported = ", ".join(sorted(PROVIDER_ENV_VARS))
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: {supported}")
    return normalized


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


def get_api_key(provider: str) -> str | None:
    """Return an API key for a supported provider, or None when unset."""
    normalized = _normalize_provider(provider)
    return _read_env(PROVIDER_ENV_VARS[normalized])


def require_api_key(provider: str) -> str:
    """Return configured API key for a provider or raise ValueError."""
    normalized = _normalize_provider(provider)
    key = get_api_key(normalized)
    if key is None:
        raise ValueError(f"Missing API key for provider: {normalized}")
    return key


def configured_llm_providers() -> list[str]:
    """List configured LLM providers without exposing secret values."""
    return [provider for provider in PROVIDER_ENV_VARS if get_api_key(provider) is not None]


def get_safe_config_summary() -> dict[str, bool]:
    """Return non-secret configuration state suitable for logs or reports."""
    return {
        "groq_configured": has_groq_api_key(),
        "openrouter_configured": has_openrouter_api_key(),
    }


# Backward-friendly alias for call sites that prefer provider terminology.
get_provider_api_key = get_api_key
