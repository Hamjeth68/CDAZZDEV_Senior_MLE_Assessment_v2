from __future__ import annotations

import json
import math
import time
from typing import Any

import pandas as pd

from shared.finance_data import fetch_ohlcv
from shared.llm_client import LLMClient
from shared.news import fetch_headlines
from task3_agentic.src.observability import log_tool_call
from task3_agentic.src.schemas import (
    NewsItem,
    NewsPayload,
    PriceBar,
    PriceDataPayload,
    SentimentItem,
    SentimentPayload,
    ToolError,
    ToolResult,
    VolatilityPayload,
    WebSearchItem,
    WebSearchPayload,
)


def get_price_data(ticker: str, period: str) -> ToolResult:
    start = time.perf_counter()
    inputs = {"ticker": ticker, "period": period}
    try:
        symbol = _normalize_ticker(ticker)
        if not period or not period.strip():
            raise ValueError("period must be non-empty")
        prices = fetch_ohlcv(symbol, period=period.strip())
        payload = PriceDataPayload(
            ticker=symbol,
            period=period.strip(),
            rows=len(prices),
            latest_close=_clean_float(prices["close"].dropna().iloc[-1]) if not prices["close"].dropna().empty else None,
            prices=_price_bars(prices),
        )
        result = ToolResult(status="success", tool_name="get_price_data", data=payload.model_dump(mode="json"))
    except Exception as exc:
        result = _error_result("get_price_data", exc)
    _trace("get_price_data", inputs, result, start)
    return result


def get_news(ticker: str, n: int) -> ToolResult:
    start = time.perf_counter()
    inputs = {"ticker": ticker, "n": n}
    try:
        symbol = _normalize_ticker(ticker)
        if n < 0:
            raise ValueError("n must be greater than or equal to 0")
        news = fetch_headlines(symbol, min_headlines=n)
        headlines = [
            NewsItem(
                title=headline.title,
                source=headline.source,
                published_at=headline.published_at,
                url=str(headline.url) if headline.url is not None else None,
            )
            for headline in news.headlines[:n]
        ]
        payload = NewsPayload(
            ticker=symbol,
            requested=n,
            found=len(headlines),
            sources_tried=news.sources_tried,
            warnings=news.warnings,
            headlines=headlines,
        )
        result = ToolResult(status="success", tool_name="get_news", data=payload.model_dump(mode="json"))
    except Exception as exc:
        result = _error_result("get_news", exc)
    _trace("get_news", inputs, result, start)
    return result


def calculate_volatility(ticker: str, window: int) -> ToolResult:
    start = time.perf_counter()
    inputs = {"ticker": ticker, "window": window}
    try:
        symbol = _normalize_ticker(ticker)
        if window <= 1:
            raise ValueError("window must be greater than 1")
        prices = fetch_ohlcv(symbol, period="2y")
        returns = pd.to_numeric(prices["close"], errors="coerce").pct_change().dropna()
        rolling = returns.rolling(window=window, min_periods=window).std()
        latest = rolling.dropna().iloc[-1] if not rolling.dropna().empty else None
        daily_volatility = _clean_float(latest)
        payload = VolatilityPayload(
            ticker=symbol,
            window=window,
            observations=len(returns),
            daily_volatility=daily_volatility,
            annualized_volatility=(daily_volatility * math.sqrt(252.0)) if daily_volatility is not None else None,
        )
        result = ToolResult(status="success", tool_name="calculate_volatility", data=payload.model_dump(mode="json"))
    except Exception as exc:
        result = _error_result("calculate_volatility", exc)
    _trace("calculate_volatility", inputs, result, start)
    return result


def llm_sentiment(headlines: list[str]) -> ToolResult:
    start = time.perf_counter()
    inputs = {"headlines": headlines}
    try:
        clean_headlines = [headline.strip() for headline in headlines if isinstance(headline, str) and headline.strip()]
        if not clean_headlines:
            raise ValueError("headlines must contain at least one non-empty string")
        client = LLMClient()
        prompt = (
            "Analyze the financial-news sentiment for each headline. Return JSON with keys "
            "aggregate_label, aggregate_score, and sentiments. sentiments must be a list of "
            "objects with headline, sentiment, confidence, and rationale. Sentiment must be "
            "positive, negative, or neutral.\n\nHeadlines:\n"
            + "\n".join(f"- {headline}" for headline in clean_headlines)
        )
        parsed, response = client.generate_json(
            system_prompt="You are a financial sentiment analyst. Be concise and evidence based.",
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=1200,
        )
        payload = _sentiment_payload(parsed, response.model, len(clean_headlines))
        result = ToolResult(status="success", tool_name="llm_sentiment", data=payload.model_dump(mode="json"))
    except Exception as exc:
        result = _error_result("llm_sentiment", exc)
    _trace("llm_sentiment", inputs, result, start)
    return result


def web_search(query: str) -> ToolResult:
    start = time.perf_counter()
    inputs = {"query": query}
    try:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("query must be non-empty")
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            from ddgs import DDGS
        search_query = f"{clean_query} analyst commentary stock market investment thesis"
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(search_query, max_results=8))
        snippets = [_search_item(item) for item in raw_results]
        snippets = [item for item in snippets if item is not None]
        payload = WebSearchPayload(query=clean_query, found=len(snippets), snippets=snippets)
        result = ToolResult(status="success", tool_name="web_search", data=payload.model_dump(mode="json"))
    except Exception as exc:
        result = _error_result("web_search", exc)
    _trace("web_search", inputs, result, start)
    return result


def _normalize_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker must be a non-empty symbol")
    return symbol


def _price_bars(prices: pd.DataFrame) -> list[PriceBar]:
    bars: list[PriceBar] = []
    for index, row in prices.tail(30).iterrows():
        bars.append(
            PriceBar(
                date=index.isoformat() if hasattr(index, "isoformat") else str(index),
                open=_clean_float(row.get("open")),
                high=_clean_float(row.get("high")),
                low=_clean_float(row.get("low")),
                close=_clean_float(row.get("close")),
                adj_close=_clean_float(row.get("adj_close")),
                volume=_clean_float(row.get("volume")),
            )
        )
    return bars


def _sentiment_payload(parsed: dict[str, Any], model_name: str, expected_count: int) -> SentimentPayload:
    raw_sentiments = parsed.get("sentiments", [])
    sentiments: list[SentimentItem] = []
    if isinstance(raw_sentiments, list):
        for item in raw_sentiments:
            if not isinstance(item, dict):
                continue
            sentiments.append(
                SentimentItem(
                    headline=str(item.get("headline", "")).strip(),
                    sentiment=_sentiment_label(item.get("sentiment")),
                    confidence=_bounded_float(item.get("confidence"), default=0.0, minimum=0.0, maximum=1.0),
                    rationale=str(item.get("rationale") or item.get("brief_reason") or "No rationale provided.").strip(),
                )
            )
    return SentimentPayload(
        headlines_analyzed=expected_count,
        aggregate_label=_optional_sentiment_label(parsed.get("aggregate_label")),
        aggregate_score=_bounded_float(parsed.get("aggregate_score"), default=None, minimum=-1.0, maximum=1.0),
        model_name=model_name,
        sentiments=sentiments,
    )


def _search_item(item: dict[str, Any]) -> WebSearchItem | None:
    title = str(item.get("title") or "").strip()
    snippet = str(item.get("body") or item.get("snippet") or item.get("description") or "").strip()
    if not title and not snippet:
        return None
    return WebSearchItem(
        title=title,
        snippet=snippet,
        url=item.get("href") or item.get("url"),
        source=item.get("source"),
    )


def _sentiment_label(value: Any) -> str:
    label = str(value or "neutral").strip().lower()
    if label in {"positive", "negative", "neutral"}:
        return label
    return "neutral"


def _optional_sentiment_label(value: Any) -> str | None:
    if value is None:
        return None
    return _sentiment_label(value)


def _bounded_float(value: Any, default: float | None, minimum: float, maximum: float) -> float | None:
    numeric = _clean_float(value)
    if numeric is None:
        return default
    return min(max(numeric, minimum), maximum)


def _clean_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _error_result(tool_name: str, exc: Exception) -> ToolResult:
    return ToolResult(
        status="error",
        tool_name=tool_name,
        error=ToolError(error_type=type(exc).__name__, message=str(exc)),
    )


def _trace(tool_name: str, inputs: dict[str, Any], result: ToolResult, start: float) -> None:
    duration_ms = int((time.perf_counter() - start) * 1000)
    log_tool_call(
        tool_name=tool_name,
        inputs=inputs,
        output=json.loads(result.model_dump_json()),
        duration_ms=duration_ms,
        status=result.status,
    )
