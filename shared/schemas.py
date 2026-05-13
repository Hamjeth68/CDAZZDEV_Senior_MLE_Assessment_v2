"""Pydantic schemas shared across Task 1 and Task 3."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


SentimentLabel = Literal["positive", "negative", "neutral"]
RecommendationLabel = Literal["Buy", "Hold", "Sell"]
SignalLabel = Literal["bullish", "bearish", "neutral"]
TraceStatus = Literal["success", "error"]


class SharedBaseModel(BaseModel):
    """Common Pydantic behavior for assessment data contracts."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class NewsHeadline(SharedBaseModel):
    title: str = Field(min_length=1, description="Raw headline text.")
    ticker: Optional[str] = Field(default=None, description="Related ticker when known.")
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    url: Optional[HttpUrl] = None


class NewsSentiment(SharedBaseModel):
    headline: str = Field(min_length=1)
    sentiment: SentimentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    brief_reason: str = Field(min_length=1, max_length=240)
    source: Optional[str] = None


class SentimentBatchResult(SharedBaseModel):
    ticker: str = Field(min_length=1)
    sentiments: List[NewsSentiment] = Field(default_factory=list)
    positive_count: int = Field(default=0, ge=0)
    negative_count: int = Field(default=0, ge=0)
    neutral_count: int = Field(default=0, ge=0)
    aggregate_label: Optional[SentimentLabel] = None
    aggregate_score: Optional[float] = Field(default=None, ge=-1.0, le=1.0)


class TechnicalIndicatorSnapshot(SharedBaseModel):
    ticker: Optional[str] = None
    as_of: Optional[datetime] = None
    close_price: Optional[float] = Field(default=None, ge=0.0)
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    rsi_14: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_mid: Optional[float] = None
    bollinger_lower: Optional[float] = None
    momentum_signal: Optional[SignalLabel] = None
    volume_trend: Optional[SignalLabel] = None


class EquitySummary(SharedBaseModel):
    ticker: str = Field(min_length=1)
    company_name: Optional[str] = None
    current_price: Optional[float] = Field(default=None, ge=0.0)
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = Field(default=None, ge=0.0)
    sector: Optional[str] = None
    indicator_snapshot: TechnicalIndicatorSnapshot


class LLMRecommendation(SharedBaseModel):
    recommendation: RecommendationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    key_risks: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    model_name: Optional[str] = None


class AgentToolTrace(SharedBaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    agent: str
    tool_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_preview: str = ""
    duration_ms: int = Field(ge=0)
    status: TraceStatus
    error_message: Optional[str] = None


class AgentDataBrief(SharedBaseModel):
    ticker: str = Field(min_length=1)
    price_summary: str
    volatility_summary: str
    sentiment_summary: str
    notable_signals: List[str] = Field(default_factory=list)
    tool_traces: List[AgentToolTrace] = Field(default_factory=list)
    data_gaps: List[str] = Field(default_factory=list)


class FinalResearchReport(SharedBaseModel):
    ticker: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    financial_health_summary: str
    recommendation: Optional[LLMRecommendation] = None
    top_three_risks: List[str] = Field(default_factory=list)
    hedge_strategy_recommendation: str
    supporting_evidence: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
