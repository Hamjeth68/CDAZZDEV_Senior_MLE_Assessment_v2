from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"


def cache_path(ticker: str, as_of: datetime | None = None) -> Path:
    """Return the daily cache file path for a ticker."""
    symbol = ticker.strip().upper()
    date_part = (as_of or datetime.utcnow()).date().isoformat()
    return CACHE_DIR / f"{symbol}_{date_part}.json"


def load_cached_report(ticker: str, as_of: datetime | None = None) -> dict[str, Any] | None:
    """Load today's cached Task 3 report if present and valid JSON."""
    path = cache_path(ticker, as_of=as_of)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_cached_report(ticker: str, payload: dict[str, Any], as_of: datetime | None = None) -> Path:
    """Persist a Task 3 report payload to the daily cache."""
    path = cache_path(ticker, as_of=as_of)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path
