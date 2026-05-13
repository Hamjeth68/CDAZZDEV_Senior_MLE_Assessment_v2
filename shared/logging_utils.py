"""Structured logging utilities with secret redaction safeguards."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping, Sequence
from typing import Any

# Exact key names and common substrings that indicate sensitive content.
SENSITIVE_EXACT_KEYS = {"authorization"}
SENSITIVE_SUBSTRINGS = {
    "api_key",
    "apikey",
    "token",
    "password",
    "secret",
    "private_key",
    "access_key",
    "credential",
}


REDACTION_TEXT = "***REDACTED***"


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    return key_lower in SENSITIVE_EXACT_KEYS or any(part in key_lower for part in SENSITIVE_SUBSTRINGS)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: (REDACTION_TEXT if _is_sensitive_key(str(k)) else _sanitize_value(v)) for k, v in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_value(item) for item in value]

    if isinstance(value, str):
        return _redact_known_secret_strings(value)

    return value


def _sanitize(payload: dict[str, Any]) -> dict[str, Any]:
    return _sanitize_value(payload)


def _configured_secret_values() -> list[str]:
    candidates = [
        os.getenv("GROQ_API_KEY"),
        os.getenv("OPENROUTER_API_KEY"),
    ]
    return [value.strip() for value in candidates if value and value.strip()]


def _redact_known_secret_strings(value: str) -> str:
    redacted = value
    for secret in _configured_secret_values():
        redacted = redacted.replace(secret, REDACTION_TEXT)
    return redacted


def get_logger(name: str = "cdazzdev") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_structured(
    logger: logging.Logger,
    level: int,
    event: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Emit a JSON log record after recursively redacting sensitive values."""
    payload = payload or {}
    safe_payload = _sanitize(payload)
    safe_event = _redact_known_secret_strings(event)
    logger.log(level, json.dumps({"event": safe_event, "payload": safe_payload}, default=str))


class StructuredLogger:
    """Small convenience wrapper for structured JSON event logs."""

    def __init__(self, name: str = "cdazzdev") -> None:
        self.logger = get_logger(name)

    def info(self, event: str, **payload: Any) -> None:
        log_structured(self.logger, logging.INFO, event, payload)

    def warning(self, event: str, **payload: Any) -> None:
        log_structured(self.logger, logging.WARNING, event, payload)

    def error(self, event: str, **payload: Any) -> None:
        log_structured(self.logger, logging.ERROR, event, payload)
