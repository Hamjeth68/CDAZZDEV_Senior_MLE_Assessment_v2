"""LLM client abstraction with Groq primary and OpenRouter fallback."""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests

from shared.config import require_api_key
from shared.errors import (
    LLMProviderError,
    LLMValidationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
)
from shared.logging_utils import get_logger, log_structured

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
OPENROUTER_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"

DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 2000
DEFAULT_RETRIES = 2
REQUEST_TIMEOUT_SECONDS = 60
TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """Raw LLM text plus provider metadata."""

    content: str
    provider: str
    model: str
    duration_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    fallback_used: bool = False
    retry_attempts: int = 0

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


class BaseProvider(ABC):
    """Provider interface for chat-completion style LLMs."""

    name: str
    model: str

    @abstractmethod
    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        """Generate raw text from the provider."""

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> tuple[dict[str, Any], LLMResponse]:
        json_prompt = (
            f"{user_prompt}\n\nReturn valid JSON only. "
            "Do not wrap the JSON in markdown fences."
        )
        response = self.generate_text(system_prompt, json_prompt, temperature, max_tokens)
        parsed = parse_json_response(response.content)
        if parsed is None:
            raise LLMValidationError(f"{self.name} returned text that was not valid JSON")
        return parsed, response


def parse_json_response(content: str) -> dict[str, Any] | None:
    """Parse a JSON object from raw model output, allowing common code fences."""
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class GroqProvider(BaseProvider):
    """Groq chat-completions provider."""

    name = "groq"

    def __init__(self, api_key: str | None = None, model: str = GROQ_DEFAULT_MODEL):
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise LLMProviderError("Groq SDK is not installed") from exc

        self.api_key = api_key or require_api_key("groq")
        self.model = model
        self.client = Groq(api_key=self.api_key)

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        start = time.monotonic()
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # SDK exposes several exception classes by version.
            raise _classify_provider_error(self.name, exc) from exc

        try:
            usage = getattr(completion, "usage", None)
            choice = completion.choices[0]
            content = choice.message.content or ""
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMProviderError("groq returned an unexpected response shape") from exc

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            duration_seconds=time.monotonic() - start,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )


class OpenRouterProvider(BaseProvider):
    """OpenRouter chat-completions provider."""

    name = "openrouter"

    def __init__(self, api_key: str | None = None, model: str = OPENROUTER_DEFAULT_MODEL):
        self.api_key = api_key or require_api_key("openrouter")
        self.model = model

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        start = time.monotonic()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                OPENROUTER_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise LLMProviderError(f"openrouter request failed: {exc}") from exc

        if response.status_code in {401, 403}:
            raise ProviderAuthenticationError("openrouter authentication failed")
        if response.status_code == 429:
            raise ProviderRateLimitError("openrouter rate limit exceeded")
        if response.status_code >= 400:
            raise LLMProviderError(f"openrouter HTTP {response.status_code}")

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("openrouter returned an unexpected response shape") from exc

        usage = data.get("usage") or {}
        return LLMResponse(
            content=content or "",
            provider=self.name,
            model=self.model,
            duration_seconds=time.monotonic() - start,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )


class LLMClient:
    """Unified LLM client with retries and Groq-to-OpenRouter failover."""

    def __init__(
        self,
        groq_model: str = GROQ_DEFAULT_MODEL,
        openrouter_model: str = OPENROUTER_DEFAULT_MODEL,
        max_retries: int = DEFAULT_RETRIES,
    ):
        self.max_retries = max_retries
        self.primary_provider = _build_provider(GroqProvider, model=groq_model)
        self.fallback_provider = _build_provider(OpenRouterProvider, model=openrouter_model)
        self.primary_available = self.primary_provider is not None
        self.fallback_available = self.fallback_provider is not None

        if not self.primary_available and not self.fallback_available:
            raise LLMProviderError("No LLM providers configured")

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        last_error: Exception | None = None
        for provider, is_fallback in self._providers_in_order():
            try:
                response = self._with_retries(
                    provider,
                    system_prompt,
                    user_prompt,
                    temperature,
                    max_tokens,
                    expect_json=False,
                )
                response.fallback_used = is_fallback
                return response
            except LLMProviderError as exc:
                last_error = exc
                _log_provider_error(provider.name, exc, will_fallback=not is_fallback)

        raise LLMProviderError(f"All LLM providers failed: {last_error}")

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> tuple[dict[str, Any], LLMResponse]:
        last_error: Exception | None = None
        for provider, is_fallback in self._providers_in_order():
            try:
                parsed, response = self._with_retries(
                    provider,
                    system_prompt,
                    user_prompt,
                    temperature,
                    max_tokens,
                    expect_json=True,
                )
                response.fallback_used = is_fallback
                return parsed, response
            except LLMProviderError as exc:
                last_error = exc
                _log_provider_error(provider.name, exc, will_fallback=not is_fallback)

        raise LLMProviderError(f"All LLM providers failed for JSON generation: {last_error}")

    def _providers_in_order(self) -> list[tuple[BaseProvider, bool]]:
        providers: list[tuple[BaseProvider, bool]] = []
        if self.primary_provider is not None:
            providers.append((self.primary_provider, False))
        if self.fallback_provider is not None:
            providers.append((self.fallback_provider, True))
        return providers

    def _with_retries(
        self,
        provider: BaseProvider,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        expect_json: bool,
    ) -> LLMResponse | tuple[dict[str, Any], LLMResponse]:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                result = (
                    provider.generate_json(system_prompt, user_prompt, temperature, max_tokens)
                    if expect_json
                    else provider.generate_text(system_prompt, user_prompt, temperature, max_tokens)
                )
                response = result[1] if expect_json else result
                response.retry_attempts = attempt
                return result
            except (ProviderAuthenticationError, LLMValidationError):
                raise
            except LLMProviderError:
                if attempt >= self.max_retries:
                    raise
                time.sleep(min(2**attempt, 4))

        raise LLMProviderError(f"{provider.name} retry loop exited unexpectedly")


def _build_provider(provider_cls: type[BaseProvider], model: str) -> BaseProvider | None:
    try:
        return provider_cls(model=model)
    except Exception as exc:
        log_structured(
            logger,
            logging.WARNING,
            "llm_provider_unavailable",
            {"provider": provider_cls.name, "error_type": type(exc).__name__, "error": str(exc)},
        )
        return None


def _classify_provider_error(provider: str, exc: Exception) -> LLMProviderError:
    message = str(exc)
    lower = message.lower()
    status_code = getattr(exc, "status_code", None)

    if status_code in {401, 403} or "auth" in lower or "api key" in lower:
        return ProviderAuthenticationError(f"{provider} authentication failed")
    if status_code == 429 or "rate limit" in lower:
        return ProviderRateLimitError(f"{provider} rate limit exceeded")
    if status_code in TRANSIENT_STATUS_CODES:
        return LLMProviderError(f"{provider} transient error: HTTP {status_code}")
    return LLMProviderError(f"{provider} request failed: {type(exc).__name__}")


def _log_provider_error(provider: str, exc: Exception, will_fallback: bool) -> None:
    log_structured(
        logger,
        logging.WARNING,
        "llm_provider_error",
        {
            "provider": provider,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "will_fallback": will_fallback,
        },
    )


# Backward-compatible test hook used by the verification script.
OpenRouterProvider._parse_json_response = staticmethod(parse_json_response)  # type: ignore[attr-defined]
GroqProvider._parse_json_response = staticmethod(parse_json_response)  # type: ignore[attr-defined]
