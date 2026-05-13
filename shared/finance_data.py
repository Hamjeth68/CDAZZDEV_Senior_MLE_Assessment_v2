"""Financial market data retrieval helpers built around yfinance.

The functions in this module intentionally keep date handling relative by
using yfinance periods such as ``"2y"``. That avoids stale hardcoded date
strings while still fetching enough daily observations for long-window
technical indicators such as the 200-day SMA.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
import yfinance as yf

from shared.errors import DataFetchError


OHLCV_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


def _clean_float(value: Any) -> float | None:
    """Return a finite float or ``None`` for missing, null, or non-numeric values."""
    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(numeric) or math.isinf(numeric):
        return None

    return numeric


def _safe_get(source: Any, key: str) -> Any:
    try:
        if hasattr(source, "get"):
            return source.get(key)
        return source[key]
    except Exception:
        return None


def _first_present(*sources_and_keys: tuple[Any, list[str]]) -> float | None:
    for source, keys in sources_and_keys:
        for key in keys:
            value = _clean_float(_safe_get(source, key))
            if value is not None:
                return value
    return None


def _first_text(info: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = info.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _load_fast_info(ticker_obj: yf.Ticker) -> Any:
    try:
        return ticker_obj.fast_info
    except Exception:  # pragma: no cover - network/provider specific
        return {}


def _load_info(ticker_obj: yf.Ticker) -> dict[str, Any]:
    try:
        info = ticker_obj.get_info()
    except Exception:  # pragma: no cover - network/provider specific
        return {}

    if isinstance(info, dict):
        return info
    return {}


def _metadata_value(info: dict[str, Any], fast_info: Any, info_keys: list[str], fast_keys: list[str]) -> float | None:
    return _first_present((info, info_keys), (fast_info, fast_keys))


def _legacy_metadata_value(info: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _clean_float(info.get(key))
        if value is not None:
            return value
    return None


def fetch_ohlcv(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Fetch daily OHLCV history for ``ticker``.

    Parameters
    ----------
    ticker:
        Exchange ticker symbol accepted by yfinance.
    period:
        Relative yfinance period. The default, ``"2y"``, provides at least two
        years of daily candles when yfinance has that much history available.

    Returns
    -------
    pandas.DataFrame
        A date-indexed frame with lower-case ``open``, ``high``, ``low``,
        ``close``, ``adj_close``, and ``volume`` columns. Missing source columns
        are created with ``NA`` values so downstream code can handle sparse data
        consistently.

    Raises
    ------
    DataFetchError
        If yfinance returns no daily price history or the request fails.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker must be a non-empty symbol")

    try:
        raw = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
    except Exception as exc:  # pragma: no cover - network/provider specific
        raise DataFetchError(f"Failed to fetch OHLCV history for {symbol}: {exc}") from exc

    if raw is None or raw.empty:
        raise DataFetchError(f"No OHLCV history returned for {symbol}")

    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    data = raw.rename(columns=rename_map).copy()

    for column in OHLCV_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NA

    data = data[OHLCV_COLUMNS]
    data.index.name = "date"
    return data


def fetch_ticker_metadata(ticker: str) -> dict[str, float | str | None]:
    """Fetch current metadata for ``ticker`` where yfinance exposes it.

    The returned dictionary includes current price, 52-week high, 52-week low,
    and PE ratio. yfinance metadata varies by asset and exchange, so missing,
    null, non-finite, or non-numeric values are normalized to ``None`` instead
    of raising.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker must be a non-empty symbol")

    ticker_obj = yf.Ticker(symbol)
    info = _load_info(ticker_obj)
    fast_info = _load_fast_info(ticker_obj)

    return {
        "ticker": symbol,
        "company_name": _first_text(info, ["longName", "shortName"]),
        "current_price": _metadata_value(
            info,
            fast_info,
            ["currentPrice", "regularMarketPrice", "previousClose"],
            ["last_price", "lastPrice", "regular_market_previous_close"],
        ),
        "week_52_high": _metadata_value(
            info,
            fast_info,
            ["fiftyTwoWeekHigh"],
            ["year_high", "yearHigh"],
        ),
        "week_52_low": _metadata_value(
            info,
            fast_info,
            ["fiftyTwoWeekLow"],
            ["year_low", "yearLow"],
        ),
        "pe_ratio": _legacy_metadata_value(info, ["trailingPE", "forwardPE"]),
    }


def fetch_equity_data(ticker: str, period: str = "2y") -> dict[str, Any]:
    """Fetch normalized daily prices and best-effort ticker metadata.

    This convenience wrapper keeps price-history errors explicit while allowing
    partial metadata. The result is suitable for feeding into the indicator
    layer and the shared Pydantic equity summary schema.
    """
    return {
        "prices": fetch_ohlcv(ticker, period=period),
        "metadata": fetch_ticker_metadata(ticker),
    }
