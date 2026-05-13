"""LLM-backed headline sentiment analysis for Task 1."""

from __future__ import annotations

import logging
from typing import Iterable

from pydantic import ValidationError

from shared.errors import LLMProviderError
from shared.llm_client import LLMClient
from shared.logging_utils import get_logger, log_structured
from shared.prompts import PER_HEADLINE_SENTIMENT_PROMPT
from shared.schemas import NewsHeadline, NewsSentiment, SentimentBatchResult

logger = get_logger(__name__)


def analyze_headline_sentiment(
    headline: NewsHeadline | str,
    llm_client: LLMClient | None = None,
) -> NewsSentiment | None:
    """Classify one headline, returning ``None`` when validation/provider calls fail."""
    title = headline.title if isinstance(headline, NewsHeadline) else str(headline)
    source = headline.source if isinstance(headline, NewsHeadline) else None

    user_prompt = (
        "Classify this equity news headline for likely stock-market sentiment.\n"
        f"Headline: {title}"
    )

    try:
        client = llm_client or LLMClient()
        payload, _ = client.generate_json(
            PER_HEADLINE_SENTIMENT_PROMPT,
            user_prompt,
            temperature=0.0,
            max_tokens=300,
        )
        payload.setdefault("headline", title)
        if source and not payload.get("source"):
            payload["source"] = source
        return NewsSentiment.model_validate(payload)
    except (ValidationError, LLMProviderError, ValueError) as exc:
        log_structured(
            logger,
            logging.WARNING,
            "headline_sentiment_failed",
            {"headline": title, "error_type": type(exc).__name__, "error": str(exc)},
        )
        return None


def analyze_news_sentiment(
    ticker: str,
    headlines: Iterable[NewsHeadline | str],
    llm_client: LLMClient | None = None,
) -> SentimentBatchResult:
    """Analyze each headline independently and aggregate valid classifications."""
    normalized_ticker = ticker.strip().upper()
    sentiments: list[NewsSentiment] = []
    try:
        client = llm_client or LLMClient()
    except LLMProviderError as exc:
        log_structured(
            logger,
            logging.WARNING,
            "sentiment_client_unavailable",
            {"ticker": normalized_ticker, "error": str(exc)},
        )
        raise

    for headline in headlines:
        sentiment = analyze_headline_sentiment(headline, llm_client=client)
        if sentiment is not None:
            sentiments.append(sentiment)

    return build_sentiment_batch_result(normalized_ticker, sentiments)


def build_sentiment_batch_result(
    ticker: str,
    sentiments: Iterable[NewsSentiment],
) -> SentimentBatchResult:
    """Build aggregate sentiment counts and weighted score from validated rows."""
    rows = list(sentiments)
    positive_count = sum(item.sentiment == "positive" for item in rows)
    negative_count = sum(item.sentiment == "negative" for item in rows)
    neutral_count = sum(item.sentiment == "neutral" for item in rows)

    score = None
    aggregate_label = None
    if rows:
        signed_values = []
        for item in rows:
            if item.sentiment == "positive":
                direction = 1.0
            elif item.sentiment == "negative":
                direction = -1.0
            else:
                direction = 0.0
            signed_values.append(direction * item.confidence)
        score = sum(signed_values) / len(rows)
        if score > 0.15:
            aggregate_label = "positive"
        elif score < -0.15:
            aggregate_label = "negative"
        else:
            aggregate_label = "neutral"

    return SentimentBatchResult(
        ticker=ticker.strip().upper(),
        sentiments=rows,
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        aggregate_label=aggregate_label,
        aggregate_score=score,
    )
