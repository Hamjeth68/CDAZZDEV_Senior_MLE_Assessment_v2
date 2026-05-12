"""Pydantic schemas shared across Task 1 and Task 3."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class NewsHeadline(BaseModel):
    title: str
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    url: Optional[str] = None


class NewsSentiment(BaseModel):
    headline: str
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    brief_reason: str


class SentimentBatchResult(BaseModel):
    ticker: str
    sentiments: List[NewsSentiment] = Field(default_factory=list)
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0


class TechnicalIndicatorSnapshot(BaseModel):
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    momentum_signal: Optional[Literal["bullish", "bearish", "neutral"]] = None


class EquitySummary(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    current_price: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    pe_ratio: Optional[float] = None
    indicator_snapshot: TechnicalIndicatorSnapshot


class LLMRecommendation(BaseModel):
    recommendation: Literal["Buy", "Hold", "Sell"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    key_risks: List[str] = Field(default_factory=list)


class AgentToolTrace(BaseModel):
    timestamp: datetime
    session_id: str
    agent: str
    tool_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_preview: str
    duration_ms: int
    status: Literal["success", "error"]


class AgentDataBrief(BaseModel):
    ticker: str
    price_summary: str
    volatility_summary: str
    sentiment_summary: str
    notable_signals: List[str] = Field(default_factory=list)


class FinalResearchReport(BaseModel):
    ticker: str
    generated_at: datetime
    financial_health_summary: str
    top_three_risks: List[str] = Field(default_factory=list)
    hedge_strategy_recommendation: str
    supporting_evidence: List[str] = Field(default_factory=list)
