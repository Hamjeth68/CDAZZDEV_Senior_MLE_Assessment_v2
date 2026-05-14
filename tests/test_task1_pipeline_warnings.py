from __future__ import annotations

import pandas as pd
import pytest

from shared.errors import LLMProviderError
from shared.schemas import EquitySummary, TechnicalIndicatorSnapshot
from task1_financial.src import pipeline
from task1_financial.src.sentiment_service import analyze_news_sentiment
from task1_financial.src.signal_reasoner import generate_recommendation


class FailingRecommendationClient:
    def generate_json(self, *args, **kwargs):
        raise LLMProviderError("provider offline")


def _summary() -> EquitySummary:
    return EquitySummary(
        ticker="MSFT",
        current_price=420.0,
        indicator_snapshot=TechnicalIndicatorSnapshot(
            ticker="MSFT",
            close_price=420.0,
            rsi_14=55.0,
            momentum_signal="bullish",
        ),
    )


def test_sentiment_client_setup_failure_is_propagated(monkeypatch):
    class UnavailableClient:
        def __init__(self):
            raise LLMProviderError("No LLM providers configured")

    monkeypatch.setattr("task1_financial.src.sentiment_service.LLMClient", UnavailableClient)

    with pytest.raises(LLMProviderError, match="No LLM providers configured"):
        analyze_news_sentiment("msft", ["Microsoft announces new AI chips"])


def test_recommendation_failure_is_propagated():
    with pytest.raises(LLMProviderError, match="provider offline"):
        generate_recommendation(_summary(), None, llm_client=FailingRecommendationClient())


def test_pipeline_records_sentiment_and_recommendation_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "fetch_ohlcv", lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(pipeline, "fetch_ticker_metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr(pipeline, "_fetch_extended_metadata", lambda *args, **kwargs: {})

    class NewsResult:
        headlines = []
        warnings = []

    monkeypatch.setattr(pipeline, "fetch_headlines", lambda *args, **kwargs: NewsResult())
    monkeypatch.setattr(
        pipeline,
        "analyze_news_sentiment",
        lambda *args, **kwargs: (_ for _ in ()).throw(LLMProviderError("sentiment offline")),
    )
    monkeypatch.setattr(
        pipeline,
        "generate_recommendation",
        lambda *args, **kwargs: (_ for _ in ()).throw(LLMProviderError("recommendation offline")),
    )

    result = pipeline.run_equity_research(
        "msft",
        output_dir=tmp_path,
        llm_client=object(),
        render_reports=False,
    )

    assert any("sentiment_failed: sentiment offline" in warning for warning in result["warnings"])
    assert any("recommendation_failed: recommendation offline" in warning for warning in result["warnings"])
    assert result["recommendation"]["model_name"] == "fallback-rule"
