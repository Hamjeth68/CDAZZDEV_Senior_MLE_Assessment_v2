from types import SimpleNamespace

import pandas as pd
import pytest

from shared.errors import LLMProviderError
from shared.schemas import EquitySummary, NewsHeadline, SentimentBatchResult, TechnicalIndicatorSnapshot
from task1_financial.src import pipeline
from task1_financial.src import sentiment_service
from task1_financial.src import signal_reasoner
from task1_financial.src.signal_reasoner import generate_recommendation


def test_analyze_news_sentiment_propagates_client_setup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable_client() -> None:
        raise LLMProviderError("No LLM providers configured")

    monkeypatch.setattr(sentiment_service, "LLMClient", unavailable_client)

    with pytest.raises(LLMProviderError, match="No LLM providers configured"):
        sentiment_service.analyze_news_sentiment("aapl", ["Apple shares rise"])


def test_generate_recommendation_propagates_provider_failure() -> None:
    summary = EquitySummary(
        ticker="AAPL",
        indicator_snapshot=TechnicalIndicatorSnapshot(ticker="AAPL", momentum_signal="bullish"),
    )
    sentiment = SentimentBatchResult(ticker="AAPL", aggregate_label="positive", aggregate_score=0.5)
    client = SimpleNamespace(
        generate_json=lambda *_, **__: (_ for _ in ()).throw(LLMProviderError("provider down"))
    )

    with pytest.raises(LLMProviderError, match="provider down"):
        generate_recommendation(summary, sentiment, llm_client=client)


def test_run_equity_research_records_llm_fallback_warnings(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def unavailable_client() -> None:
        raise LLMProviderError("No LLM providers configured")

    monkeypatch.setattr(pipeline, "fetch_ohlcv", lambda *_, **__: pd.DataFrame())
    monkeypatch.setattr(pipeline, "fetch_ticker_metadata", lambda *_: {})
    monkeypatch.setattr(pipeline, "_fetch_extended_metadata", lambda *_: {})
    monkeypatch.setattr(
        pipeline,
        "fetch_headlines",
        lambda *_, **__: SimpleNamespace(
            headlines=[NewsHeadline(title="Apple shares rise", ticker="AAPL")],
            warnings=[],
        ),
    )
    monkeypatch.setattr(sentiment_service, "LLMClient", unavailable_client)
    monkeypatch.setattr(signal_reasoner, "LLMClient", unavailable_client)

    result = pipeline.run_equity_research("aapl", output_dir=tmp_path, render_reports=False)

    assert any(warning.startswith("sentiment_failed:") for warning in result["warnings"])
    assert any(warning.startswith("recommendation_failed:") for warning in result["warnings"])
    assert result["recommendation"]["model_name"] == "fallback-rule"
