"""Structured logging utilities with basic secret redaction safeguards."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict


SENSITIVE_KEYS = {"api_key", "authorization", "token", "password", "secret"}


def _sanitize(payload: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_KEYS:
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized


def get_logger(name: str = "cdazzdev") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)
    return logger


def log_structured(logger: logging.Logger, level: int, event: str, payload: Dict[str, Any]) -> None:
    safe_payload = _sanitize(payload)
    logger.log(level, json.dumps({"event": event, "payload": safe_payload}, default=str))
