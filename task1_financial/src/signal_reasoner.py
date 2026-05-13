"""LLM recommendation reasoner for Task 1 equity summaries."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from shared.errors import LLMProviderError
from shared.llm_client import LLMClient
from shared.logging_utils import get_logger, log_structured
from shared.prompts import TECHNICAL_RECOMMENDATION_PROMPT
from shared.schemas import EquitySummary, LLMRecommendation, SentimentBatchResult

logger = get_logger(__name__)


def generate_recommendation(
    equity_summary: EquitySummary | dict[str, Any],
    sentiment: SentimentBatchResult | dict[str, Any] | None,
    llm_client: LLMClient | None = None,
) -> LLMRecommendation:
    """Ask the LLM for a Buy/Hold/Sell view and validate the structured answer."""
    summary_model = (
        equity_summary
        if isinstance(equity_summary, EquitySummary)
        else EquitySummary.model_validate(equity_summary)
    )
    sentiment_payload = _dump_model(sentiment) if sentiment is not None else {}

    user_prompt = (
        "Use the technical snapshot and aggregate news sentiment together. "
        "Explain interaction effects and avoid simply restating each metric.\n\n"
        f"Equity summary JSON:\n{json.dumps(_dump_model(summary_model), default=str)}\n\n"
        f"Sentiment aggregate JSON:\n{json.dumps(sentiment_payload, default=str)}"
    )

    try:
        client = llm_client or LLMClient()
        payload, response = client.generate_json(
            TECHNICAL_RECOMMENDATION_PROMPT,
            user_prompt,
            temperature=0.1,
            max_tokens=700,
        )
        recommendation = LLMRecommendation.model_validate(payload)
        if recommendation.model_name is None:
            recommendation.model_name = response.model
        return recommendation
    except (ValidationError, LLMProviderError, ValueError) as exc:
        log_structured(
            logger,
            logging.WARNING,
            "recommendation_failed",
            {"ticker": summary_model.ticker, "error_type": type(exc).__name__, "error": str(exc)},
        )
        return fallback_recommendation(summary_model, sentiment)


def fallback_recommendation(
    equity_summary: EquitySummary,
    sentiment: SentimentBatchResult | dict[str, Any] | None,
) -> LLMRecommendation:
    """Conservative validated fallback used when the LLM is unavailable."""
    snapshot = equity_summary.indicator_snapshot
    sentiment_label = getattr(sentiment, "aggregate_label", None)
    if isinstance(sentiment, dict):
        sentiment_label = sentiment.get("aggregate_label")

    evidence = []
    if snapshot.momentum_signal:
        evidence.append(f"Momentum signal is {snapshot.momentum_signal}.")
    if snapshot.rsi_14 is not None:
        evidence.append(f"RSI 14 is {snapshot.rsi_14:.1f}.")
    if sentiment_label:
        evidence.append(f"News sentiment aggregate is {sentiment_label}.")

    recommendation = "Hold"
    if snapshot.momentum_signal == "bullish" and sentiment_label == "positive":
        recommendation = "Buy"
    elif snapshot.momentum_signal == "bearish" and sentiment_label == "negative":
        recommendation = "Sell"

    return LLMRecommendation(
        recommendation=recommendation,
        confidence=0.35,
        rationale=(
            "LLM recommendation generation was unavailable, so this conservative "
            "fallback weighs broad momentum against aggregate sentiment."
        ),
        key_risks=[
            "Automated fallback has limited qualitative reasoning.",
            "Market data and news feeds may be delayed, incomplete, or unavailable.",
        ],
        evidence=evidence or ["Insufficient validated evidence for a directional view."],
        model_name="fallback-rule",
    )


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {}
