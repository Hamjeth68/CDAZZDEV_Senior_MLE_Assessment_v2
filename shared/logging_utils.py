"""Structured logging utilities with secret redaction safeguards."""

from __future__ import annotations

import json
import logging
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

    return value


def _sanitize(payload: dict[str, Any]) -> dict[str, Any]:
    return _sanitize_value(payload)


def get_logger(name: str = "cdazzdev") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)
    return logger


def log_structured(logger: logging.Logger, level: int, event: str, payload: dict[str, Any]) -> None:
    safe_payload = _sanitize(payload)
    logger.log(level, json.dumps({"event": event, "payload": safe_payload}, default=str))
