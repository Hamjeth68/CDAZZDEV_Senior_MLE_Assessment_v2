"""News retrieval helpers with yfinance primary and search fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.logging_utils import get_logger, log_structured
from shared.schemas import NewsHeadline

DEFAULT_HEADLINE_COUNT = 10

logger = get_logger(__name__)


@dataclass
class NewsRetrievalResult:
    """Headlines plus non-fatal retrieval metadata."""

    ticker: str
    headlines: list[NewsHeadline] = field(default_factory=list)
    sources_tried: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def found_count(self) -> int:
        return len(self.headlines)


def fetch_headlines(
    ticker: str,
    min_headlines: int = DEFAULT_HEADLINE_COUNT,
    company_name: str | None = None,
) -> NewsRetrievalResult:
    """Fetch company news without raising when providers return no results."""
    normalized_ticker = ticker.strip().upper()
    result = NewsRetrievalResult(ticker=normalized_ticker)

    yfinance_headlines = _fetch_yfinance_headlines(normalized_ticker, min_headlines)
    result.sources_tried.append("yfinance")
    result.headlines.extend(yfinance_headlines)

    if len(result.headlines) < min_headlines:
        query = company_name or normalized_ticker
        fallback_headlines = _fetch_search_headlines(query, min_headlines)
        result.sources_tried.append("duckduckgo-search")
        result.headlines = _dedupe_headlines(result.headlines + fallback_headlines)

    if not result.headlines:
        warning = f"No news found for {normalized_ticker}"
        result.warnings.append(warning)
        log_structured(
            logger,
            logging.WARNING,
            "news_retrieval_empty",
            {"ticker": normalized_ticker, "sources_tried": result.sources_tried},
        )
    elif len(result.headlines) < min_headlines:
        warning = f"Only found {len(result.headlines)} headlines for {normalized_ticker}"
        result.warnings.append(warning)
        log_structured(
            logger,
            logging.WARNING,
            "news_retrieval_partial",
            {
                "ticker": normalized_ticker,
                "found_count": len(result.headlines),
                "requested_minimum": min_headlines,
                "sources_tried": result.sources_tried,
            },
        )

    result.headlines = result.headlines[:min_headlines]
    return result


def get_news_headlines(
    ticker: str,
    min_headlines: int = DEFAULT_HEADLINE_COUNT,
    company_name: str | None = None,
) -> list[NewsHeadline]:
    """Compatibility helper for callers that only need headline objects."""
    return fetch_headlines(ticker, min_headlines=min_headlines, company_name=company_name).headlines


def _fetch_yfinance_headlines(ticker: str, count: int) -> list[NewsHeadline]:
    try:
        import yfinance as yf
    except ImportError:
        _log_news_provider_warning("yfinance", ticker, "package not installed")
        return []

    try:
        ticker_obj = yf.Ticker(ticker)
        raw_items = getattr(ticker_obj, "news", None) or []
        if not raw_items:
            raw_items = ticker_obj.get_news(count=count, tab="news")
    except Exception as exc:
        _log_news_provider_warning("yfinance", ticker, str(exc))
        return []

    headlines: list[NewsHeadline] = []
    for item in raw_items or []:
        headline = _headline_from_yfinance_item(item)
        if headline is not None:
            headlines.append(headline)
    return _dedupe_headlines(headlines)


def _fetch_search_headlines(query: str, count: int) -> list[NewsHeadline]:
    ddgs_cls = _load_ddgs()
    if ddgs_cls is None:
        _log_news_provider_warning("duckduckgo-search", query, "package not installed")
        return []

    search_query = f"{query} stock news"
    try:
        with ddgs_cls() as ddgs:
            if hasattr(ddgs, "news"):
                raw_items = list(ddgs.news(search_query, max_results=count))
            else:
                raw_items = list(ddgs.text(search_query, max_results=count))
    except Exception as exc:
        _log_news_provider_warning("duckduckgo-search", query, str(exc))
        return []

    headlines: list[NewsHeadline] = []
    for item in raw_items:
        headline = _headline_from_search_item(item)
        if headline is not None:
            headlines.append(headline)
    return _dedupe_headlines(headlines)


def _load_ddgs() -> Any | None:
    try:
        from duckduckgo_search import DDGS

        return DDGS
    except ImportError:
        try:
            from ddgs import DDGS

            return DDGS
        except ImportError:
            return None


def _headline_from_yfinance_item(item: dict[str, Any]) -> NewsHeadline | None:
    content = item.get("content") if isinstance(item.get("content"), dict) else item
    title = _first_str(content, ("title", "headline", "name"))
    if not title:
        return None

    publisher = _first_str(content, ("publisher", "provider", "source"))
    if isinstance(content.get("provider"), dict):
        publisher = publisher or _first_str(content["provider"], ("displayName", "name"))

    url = _extract_url(content)
    published_at = _parse_datetime(
        content.get("pubDate")
        or content.get("displayTime")
        or content.get("providerPublishTime")
        or content.get("published_at")
    )

    return NewsHeadline(title=title, source=publisher, published_at=published_at, url=url)


def _headline_from_search_item(item: dict[str, Any]) -> NewsHeadline | None:
    title = _first_str(item, ("title", "headline"))
    if not title:
        return None
    return NewsHeadline(
        title=title,
        source=_first_str(item, ("source", "publisher")),
        published_at=_parse_datetime(item.get("date") or item.get("published")),
        url=_first_str(item, ("url", "href")),
    )


def _first_str(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_url(payload: dict[str, Any]) -> str | None:
    direct_url = _first_str(payload, ("url", "link", "canonicalUrl"))
    if direct_url:
        return direct_url

    click_through = payload.get("clickThroughUrl")
    if isinstance(click_through, dict):
        return _first_str(click_through, ("url",))
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _dedupe_headlines(headlines: list[NewsHeadline]) -> list[NewsHeadline]:
    seen: set[tuple[str, str | None]] = set()
    deduped: list[NewsHeadline] = []
    for headline in headlines:
        key = (headline.title.casefold(), headline.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(headline)
    return deduped


def _log_news_provider_warning(provider: str, query: str, error: str) -> None:
    log_structured(
        logger,
        logging.WARNING,
        "news_provider_warning",
        {"provider": provider, "query": query, "error": error},
    )
