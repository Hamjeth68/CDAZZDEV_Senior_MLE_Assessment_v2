from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


ToolStatus = Literal["success", "error"]
SentimentLabel = Literal["positive", "negative", "neutral"]


class Task3BaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class ToolError(Task3BaseModel):
    error_type: str
    message: str


class ToolResult(Task3BaseModel):
    status: ToolStatus
    tool_name: str
    data: dict[str, Any] | None = None
    error: ToolError | None = None


class PriceBar(Task3BaseModel):
    date: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adj_close: float | None = None
    volume: float | None = None


class PriceDataPayload(Task3BaseModel):
    ticker: str = Field(min_length=1)
    period: str = Field(min_length=1)
    rows: int = Field(ge=0)
    latest_close: float | None = None
    prices: list[PriceBar] = Field(default_factory=list)


class NewsItem(Task3BaseModel):
    title: str = Field(min_length=1)
    source: str | None = None
    published_at: datetime | None = None
    url: HttpUrl | str | None = None


class NewsPayload(Task3BaseModel):
    ticker: str = Field(min_length=1)
    requested: int = Field(ge=0)
    found: int = Field(ge=0)
    sources_tried: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    headlines: list[NewsItem] = Field(default_factory=list)


class VolatilityPayload(Task3BaseModel):
    ticker: str = Field(min_length=1)
    window: int = Field(gt=1)
    observations: int = Field(ge=0)
    daily_volatility: float | None = None
    annualized_volatility: float | None = None


class SentimentItem(Task3BaseModel):
    headline: str = Field(min_length=1)
    sentiment: SentimentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


class SentimentPayload(Task3BaseModel):
    headlines_analyzed: int = Field(ge=0)
    aggregate_label: SentimentLabel | None = None
    aggregate_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    model_name: str | None = None
    sentiments: list[SentimentItem] = Field(default_factory=list)


class WebSearchItem(Task3BaseModel):
    title: str
    snippet: str
    url: str | None = None
    source: str | None = None


class WebSearchPayload(Task3BaseModel):
    query: str = Field(min_length=1)
    found: int = Field(ge=0)
    snippets: list[WebSearchItem] = Field(default_factory=list)


class AgentTraceRecord(Task3BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    agent: str
    tool_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_preview: str = Field(max_length=200)
    duration_ms: int = Field(ge=0)
    status: ToolStatus
