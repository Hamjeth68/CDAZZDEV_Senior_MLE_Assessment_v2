"""End-to-end Task 1 equity research pipeline."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from shared.errors import DataFetchError, LLMProviderError
from shared.finance_data import fetch_ohlcv, fetch_ticker_metadata
from shared.indicators import add_technical_indicators, latest_indicator_snapshot
from shared.llm_client import LLMClient
from shared.logging_utils import get_logger, log_structured
from shared.news import fetch_headlines
from shared.schemas import EquitySummary, NewsHeadline, SentimentBatchResult, TechnicalIndicatorSnapshot

from task1_financial.src.report_renderer import write_report_files
from task1_financial.src.sentiment_service import analyze_news_sentiment, build_sentiment_batch_result
from task1_financial.src.signal_reasoner import fallback_recommendation, generate_recommendation

logger = get_logger(__name__)


def run_equity_research(
    ticker: str,
    period: str = "2y",
    output_dir: str | Path = "task1_financial/outputs",
    min_headlines: int = 10,
    llm_client: LLMClient | None = None,
    render_reports: bool = True,
) -> dict[str, Any]:
    """Run the complete equity research workflow for one ticker.

    The pipeline records warnings and continues when metadata, news, sentiment,
    recommendation, or rendering fail. Price history is the only hard dependency
    for technical analysis, but even that failure returns a structured result.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker must be a non-empty symbol")

    warnings: list[str] = []
    prices = pd.DataFrame()
    indicators = pd.DataFrame()
    metadata: dict[str, Any] = {"ticker": symbol}
    headlines: list[NewsHeadline] = []
    generated_at = datetime.utcnow()

    try:
        prices = fetch_ohlcv(symbol, period=period)
    except (DataFetchError, ValueError) as exc:
        _warn(warnings, "ohlcv_fetch_failed", symbol, exc)

    try:
        metadata.update(fetch_ticker_metadata(symbol))
        metadata.update(_fetch_extended_metadata(symbol))
    except Exception as exc:
        _warn(warnings, "metadata_fetch_failed", symbol, exc)

    if not prices.empty:
        try:
            indicators = add_technical_indicators(prices)
            snapshot = latest_indicator_snapshot(indicators)
            snapshot.ticker = symbol
            snapshot.as_of = _latest_timestamp(indicators)
            snapshot.close_price = _latest_numeric(prices, "close")
            snapshot.bollinger_mid = _latest_numeric(indicators, "bollinger_middle")
            snapshot.volume_trend = _derive_volume_trend(prices)
        except Exception as exc:
            _warn(warnings, "indicator_compute_failed", symbol, exc)
            snapshot = TechnicalIndicatorSnapshot(ticker=symbol)
    else:
        snapshot = TechnicalIndicatorSnapshot(ticker=symbol)

    current_price = metadata.get("current_price") or snapshot.close_price
    equity_summary = EquitySummary(
        ticker=symbol,
        company_name=metadata.get("company_name"),
        current_price=current_price,
        week_52_high=metadata.get("week_52_high"),
        week_52_low=metadata.get("week_52_low"),
        pe_ratio=metadata.get("pe_ratio"),
        market_cap=metadata.get("market_cap"),
        sector=metadata.get("sector"),
        indicator_snapshot=snapshot,
    )

    try:
        news_result = fetch_headlines(symbol, min_headlines=min_headlines, company_name=equity_summary.company_name)
        headlines = news_result.headlines
        warnings.extend(news_result.warnings)
    except Exception as exc:
        _warn(warnings, "news_fetch_failed", symbol, exc)

    try:
        sentiment = analyze_news_sentiment(symbol, headlines, llm_client=llm_client)
    except (LLMProviderError, ValueError) as exc:
        _warn(warnings, "sentiment_failed", symbol, exc)
        sentiment = build_sentiment_batch_result(symbol, [])

    try:
        recommendation = generate_recommendation(equity_summary, sentiment, llm_client=llm_client)
    except (LLMProviderError, ValueError) as exc:
        _warn(warnings, "recommendation_failed", symbol, exc)
        recommendation = fallback_recommendation(equity_summary, sentiment)

    outputs: dict[str, str | None] = {}
    if render_reports:
        try:
            outputs = write_report_files(equity_summary, sentiment, recommendation, headlines, prices, output_dir)
        except Exception as exc:
            _warn(warnings, "report_render_failed", symbol, exc)

    return {
        "ticker": symbol,
        "generated_at": generated_at.isoformat(),
        "equity_summary": equity_summary.model_dump(mode="json"),
        "sentiment": sentiment.model_dump(mode="json"),
        "recommendation": recommendation.model_dump(mode="json"),
        "headlines": [headline.model_dump(mode="json") for headline in headlines],
        "indicator_rows": len(indicators),
        "price_rows": len(prices),
        "outputs": outputs,
        "warnings": warnings,
    }


def build_equity_summary(ticker: str, metadata: dict[str, Any], snapshot: TechnicalIndicatorSnapshot) -> dict[str, Any]:
    """Build an ``EquitySummary`` dictionary for notebook/test reuse."""
    summary = EquitySummary(
        ticker=ticker.strip().upper(),
        company_name=metadata.get("company_name"),
        current_price=metadata.get("current_price") or snapshot.close_price,
        week_52_high=metadata.get("week_52_high"),
        week_52_low=metadata.get("week_52_low"),
        pe_ratio=metadata.get("pe_ratio"),
        market_cap=metadata.get("market_cap"),
        sector=metadata.get("sector"),
        indicator_snapshot=snapshot,
    )
    return summary.model_dump(mode="json")


def _fetch_extended_metadata(ticker: str) -> dict[str, Any]:
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).get_info()
    except Exception:
        return {}
    if not isinstance(info, dict):
        return {}
    return {
        "market_cap": _clean_float(info.get("marketCap")),
        "sector": info.get("sector") if isinstance(info.get("sector"), str) else None,
    }


def _latest_timestamp(frame: pd.DataFrame) -> datetime | None:
    if frame.empty:
        return None
    value = frame.index[-1]
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    return None


def _latest_numeric(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame.columns:
        return None
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    return None if series.empty else float(series.iloc[-1])


def _derive_volume_trend(prices: pd.DataFrame) -> str | None:
    if prices.empty or "volume" not in prices.columns:
        return None
    volume = pd.to_numeric(prices["volume"], errors="coerce")
    recent = volume.tail(20).mean()
    prior = volume.tail(60).head(40).mean()
    if pd.isna(recent) or pd.isna(prior) or prior == 0:
        return None
    if recent > prior * 1.1:
        return "bullish"
    if recent < prior * 0.9:
        return "bearish"
    return "neutral"


def _clean_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _warn(warnings: list[str], event: str, ticker: str, exc: Exception) -> None:
    message = f"{event}: {exc}"
    warnings.append(message)
    log_structured(
        logger,
        logging.WARNING,
        event,
        {"ticker": ticker, "error_type": type(exc).__name__, "error": str(exc)},
    )

