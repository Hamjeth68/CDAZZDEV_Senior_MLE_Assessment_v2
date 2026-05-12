"""LLM provider abstraction layer.

This module provides a unified interface for interacting with multiple LLM providers
(OpenRouter primary, Groq fallback) with automatic failover, structured JSON support,
and comprehensive error handling.

Architecture:
- BaseProvider: Abstract interface for all LLM providers
- OpenRouterProvider: Uses OpenRouter API via requests
- GroqProvider: Uses Groq SDK (fallback)
- LLMClient: Unified client with retry/failover logic
- LLMResponse: Structured output metadata
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import requests

from shared.config import require_api_key
from shared.errors import (
    LLMProviderError,
    LLMValidationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
)
from shared.logging_utils import get_logger

# Provider endpoints and defaults
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = "meta-llama/llama-3-70b-instruct"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Request parameters
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000
REQUEST_TIMEOUT_SECONDS = 60

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """Structured response from LLM provider with metadata."""

    content: str
    """The generated text content."""

    provider: str
    """Name of the provider that generated the response."""

    model: str
    """Model identifier used."""

    duration_seconds: float
    """Time taken to generate response."""

    input_tokens: int | None = None
    """Number of input tokens (if available)."""

    output_tokens: int | None = None
    """Number of output tokens (if available)."""

    fallback_used: bool = False
    """Whether fallback provider was used due to primary failure."""

    retry_attempts: int = 0
    """Number of retries performed."""

    @property
    def total_tokens(self) -> int | None:
        """Total tokens used (input + output)."""
        if self.input_tokens is not None and self.output_tokens is not None:
            return self.input_tokens + self.output_tokens
        return None


class BaseProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        """Generate text using the provider.

        Args:
            system_prompt: System role/context
            user_prompt: User message
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            ProviderAuthenticationError: If authentication fails
            ProviderRateLimitError: If rate limit is exceeded
            LLMProviderError: For other provider errors
        """

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> tuple[dict, LLMResponse]:
        """Generate valid JSON using the provider.

        Args:
            system_prompt: System role/context
            user_prompt: User message
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (parsed_dict, LLMResponse)

        Raises:
            LLMValidationError: If JSON parsing fails after retries
            ProviderAuthenticationError: If authentication fails
            ProviderRateLimitError: If rate limit is exceeded
            LLMProviderError: For other provider errors
        """


class OpenRouterProvider(BaseProvider):
    """OpenRouter LLM provider using the requests library."""

    def __init__(self, api_key: str | None = None, model: str = OPENROUTER_DEFAULT_MODEL):
        """Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (loaded from config if None)
            model: Model identifier to use
        """
        self.api_key = api_key or require_api_key("openrouter")
        self.model = model
        self.endpoint = OPENROUTER_ENDPOINT

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        """Generate text via OpenRouter API."""
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            # Handle authentication errors
            if response.status_code == 401:
                logger.error("OpenRouter authentication failed")
                raise ProviderAuthenticationError("OpenRouter API key is invalid or missing")

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("OpenRouter rate limit exceeded")
                raise ProviderRateLimitError("OpenRouter rate limit exceeded")

            # Handle other HTTP errors
            response.raise_for_status()

            data = response.json()

            # Extract response content
            if "choices" not in data or len(data["choices"]) == 0:
                raise LLMProviderError("Invalid response structure from OpenRouter")

            content = data["choices"][0]["message"]["content"]

            # Extract token usage if available
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")

            duration = time.time() - start_time

            logger.info(
                "OpenRouter text generation succeeded",
                extra={
                    "model": self.model,
                    "duration_seconds": duration,
                    "output_tokens": output_tokens,
                },
            )

            return LLMResponse(
                content=content,
                provider="openrouter",
                model=self.model,
                duration_seconds=duration,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except requests.exceptions.Timeout:
            logger.error("OpenRouter request timed out")
            raise LLMProviderError("OpenRouter request timed out")
        except requests.exceptions.RequestException as e:
            logger.error("OpenRouter request failed", extra={"error": str(e)})
            raise LLMProviderError(f"OpenRouter request failed: {str(e)}")

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> tuple[dict, LLMResponse]:
        """Generate JSON via OpenRouter API with retry on parse failure."""
        # Append JSON instruction to user prompt
        json_prompt = (
            user_prompt
            + "\n\nRespond with valid JSON only. Do not include markdown formatting or explanations."
        )

        response = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=json_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Attempt to parse JSON
        parsed_json = self._parse_json_response(response.content)
        if parsed_json is not None:
            return parsed_json, response

        # Retry once on parse failure
        logger.warning("OpenRouter JSON parsing failed, retrying...")
        response = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=json_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        parsed_json = self._parse_json_response(response.content)
        if parsed_json is not None:
            response.retry_attempts = 1
            return parsed_json, response

        # Final failure
        logger.error("OpenRouter JSON parsing failed after retry")
        raise LLMValidationError(
            f"Failed to parse JSON from OpenRouter after retry: {response.content[:200]}"
        )

    @staticmethod
    def _parse_json_response(content: str) -> dict | None:
        """Safely parse JSON from response content.

        Returns None if parsing fails, parsed dict otherwise.
        """
        try:
            # Clean up common markdown formatting
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return None


class GroqProvider(BaseProvider):
    """Groq LLM provider using the Groq SDK."""

    def __init__(self, api_key: str | None = None, model: str = GROQ_DEFAULT_MODEL):
        """Initialize Groq provider.

        Args:
            api_key: Groq API key (loaded from config if None)
            model: Model identifier to use

        Raises:
            LLMProviderError: If Groq SDK is not installed
        """
        try:
            from groq import Groq
        except ImportError:
            raise LLMProviderError(
                "Groq SDK not installed. Install with: pip install groq"
            )

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
        """Generate text via Groq API."""
        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content

            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else None
            output_tokens = usage.completion_tokens if usage else None

            duration = time.time() - start_time

            logger.info(
                "Groq text generation succeeded",
                extra={
                    "model": self.model,
                    "duration_seconds": duration,
                    "output_tokens": output_tokens,
                },
            )

            return LLMResponse(
                content=content,
                provider="groq",
                model=self.model,
                duration_seconds=duration,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except Exception as e:
            error_msg = str(e)

            # Handle authentication errors
            if "401" in error_msg or "authentication" in error_msg.lower():
                logger.error("Groq authentication failed")
                raise ProviderAuthenticationError(f"Groq authentication failed: {error_msg}")

            # Handle rate limiting
            if "429" in error_msg or "rate" in error_msg.lower():
                logger.warning("Groq rate limit exceeded")
                raise ProviderRateLimitError(f"Groq rate limit exceeded: {error_msg}")

            logger.error("Groq request failed", extra={"error": error_msg})
            raise LLMProviderError(f"Groq request failed: {error_msg}")

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> tuple[dict, LLMResponse]:
        """Generate JSON via Groq API with retry on parse failure."""
        # Append JSON instruction to user prompt
        json_prompt = (
            user_prompt
            + "\n\nRespond with valid JSON only. Do not include markdown formatting or explanations."
        )

        response = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=json_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Attempt to parse JSON
        parsed_json = self._parse_json_response(response.content)
        if parsed_json is not None:
            return parsed_json, response

        # Retry once on parse failure
        logger.warning("Groq JSON parsing failed, retrying...")
        response = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=json_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        parsed_json = self._parse_json_response(response.content)
        if parsed_json is not None:
            response.retry_attempts = 1
            return parsed_json, response

        # Final failure
        logger.error("Groq JSON parsing failed after retry")
        raise LLMValidationError(
            f"Failed to parse JSON from Groq after retry: {response.content[:200]}"
        )

    @staticmethod
    def _parse_json_response(content: str) -> dict | None:
        """Safely parse JSON from response content.

        Returns None if parsing fails, parsed dict otherwise.
        """
        try:
            # Clean up common markdown formatting
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return None


class LLMClient:
    """Unified LLM client with automatic failover from OpenRouter to Groq.

    This client prioritizes OpenRouter as the primary provider and automatically
    falls back to Groq on authentication, rate limit, or other recoverable errors.
    """

    def __init__(
        self,
        openrouter_model: str = OPENROUTER_DEFAULT_MODEL,
        groq_model: str = GROQ_DEFAULT_MODEL,
    ):
        """Initialize LLMClient with both providers.

        Args:
            openrouter_model: Model to use for OpenRouter
            groq_model: Model to use for Groq
        """
        try:
            self.primary_provider = OpenRouterProvider(model=openrouter_model)
            self.primary_available = True
            logger.info("OpenRouter provider initialized")
        except Exception as e:
            logger.warning(f"OpenRouter initialization failed: {e}")
            self.primary_available = False

        try:
            self.fallback_provider = GroqProvider(model=groq_model)
            self.fallback_available = True
            logger.info("Groq provider initialized")
        except Exception as e:
            logger.warning(f"Groq initialization failed: {e}")
            self.fallback_available = False

        if not self.primary_available and not self.fallback_available:
            raise LLMProviderError("No LLM providers available")

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> LLMResponse:
        """Generate text with automatic failover.

        Attempts OpenRouter first. On recoverable errors (auth, rate limit, timeout),
        automatically falls back to Groq.

        Args:
            system_prompt: System role/context
            user_prompt: User message
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMProviderError: If all providers fail
        """
        # Try primary provider
        if self.primary_available:
            try:
                response = self.primary_provider.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response
            except (
                ProviderAuthenticationError,
                ProviderRateLimitError,
                LLMProviderError,
            ) as e:
                logger.warning(f"Primary provider failed, attempting fallback: {e}")

        # Try fallback provider
        if self.fallback_available:
            try:
                logger.info("Switching to fallback provider (Groq)")
                response = self.fallback_provider.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                response.fallback_used = True
                return response
            except Exception as e:
                logger.error(f"Fallback provider also failed: {e}")
                raise LLMProviderError(f"All LLM providers failed: {e}")

        raise LLMProviderError("No available LLM providers")

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> tuple[dict, LLMResponse]:
        """Generate JSON with automatic failover.

        Attempts OpenRouter first. On recoverable errors (auth, rate limit, timeout),
        automatically falls back to Groq.

        Args:
            system_prompt: System role/context
            user_prompt: User message
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (parsed_dict, LLMResponse) with metadata

        Raises:
            LLMValidationError: If JSON parsing fails on all providers
            LLMProviderError: If all providers fail
        """
        # Try primary provider
        if self.primary_available:
            try:
                parsed_json, response = self.primary_provider.generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return parsed_json, response
            except LLMValidationError:
                # JSON validation errors from primary provider are not retried on fallback
                logger.error("Primary provider JSON validation failed")
                raise
            except (
                ProviderAuthenticationError,
                ProviderRateLimitError,
                LLMProviderError,
            ) as e:
                logger.warning(f"Primary provider failed, attempting fallback: {e}")

        # Try fallback provider
        if self.fallback_available:
            try:
                logger.info("Switching to fallback provider (Groq) for JSON generation")
                parsed_json, response = self.fallback_provider.generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                response.fallback_used = True
                return parsed_json, response
            except Exception as e:
                logger.error(f"Fallback provider also failed: {e}")
                raise LLMProviderError(f"All LLM providers failed for JSON generation: {e}")

        raise LLMProviderError("No available LLM providers for JSON generation")
