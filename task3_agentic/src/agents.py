"""Restricted agents and tool wrappers for the LangGraph workflow."""

from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from shared.finance_data import fetch_equity_data
from shared.indicators import add_technical_indicators, latest_indicator_snapshot
from shared.llm_client import LLMClient
from shared.news import fetch_headlines
from shared.prompts import PER_HEADLINE_SENTIMENT_PROMPT
from shared.schemas import AgentDataBrief, AgentToolTrace, FinalResearchReport, NewsHeadline


AGENT_A_NAME = "Agent A: Data Analyst"
AGENT_B_NAME = "Agent B: Research Writer"

AGENT_A_ALLOWED_TOOLS = frozenset({"get_price_data", "calculate_volatility", "llm_sentiment"})
AGENT_B_ALLOWED_TOOLS = frozenset({"get_news", "web_search"})


class PriceDataResult(BaseModel):
    """Structured output from Agent A's price data tool."""

    ticker: str
    company_name: str | None = None
    current_price: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    pe_ratio: float | None = None
    latest_close: float | None = None
    latest_date: str | None = None
    momentum_signal: str | None = None
    indicator_summary: dict[str, Any] = Field(default_factory=dict)
    data_gaps: list[str] = Field(default_factory=list)


class VolatilityResult(BaseModel):
    """Structured output from Agent A's volatility tool."""

    ticker: str
    daily_volatility: float | None = None
    annualized_volatility: float | None = None
    observations: int = 0
    summary: str
    data_gaps: list[str] = Field(default_factory=list)


class SentimentResult(BaseModel):
    """Structured output from Agent A's sentiment tool."""

    ticker: str
    aggregate_label: str
    aggregate_score: float
    evidence: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)


class ClarificationAnswer(BaseModel):
    """Agent A's structured answer to Agent B's single clarification."""

    question: str
    answer: str
    supporting_metrics: dict[str, Any] = Field(default_factory=dict)
    data_gaps: list[str] = Field(default_factory=list)


def _trace_tool(
    session_id: str,
    agent: str,
    tool_name: str,
    inputs: dict[str, Any],
    start_time: float,
    output_preview: str,
    status: str = "success",
    error_message: str | None = None,
) -> AgentToolTrace:
    return AgentToolTrace(
        session_id=session_id,
        agent=agent,
        tool_name=tool_name,
        inputs=inputs,
        output_preview=output_preview[:500],
        duration_ms=max(0, int((time.monotonic() - start_time) * 1000)),
        status=status,  # type: ignore[arg-type]
        error_message=error_message,
    )


def _clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _fmt_money(value: float | None) -> str:
    return "unavailable" if value is None else f"${value:,.2f}"


def _fmt_ratio(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.2f}"


def _headline_titles(headlines: list[NewsHeadline]) -> list[str]:
    return [headline.title for headline in headlines if headline.title]


def get_price_data(ticker: str, period: str = "2y") -> tuple[PriceDataResult, pd.DataFrame]:
    """Fetch price history and indicators for Agent A only."""

    equity = fetch_equity_data(ticker, period=period)
    prices = equity["prices"]
    indicators = add_technical_indicators(prices)
    snapshot = latest_indicator_snapshot(indicators)

    latest_row = indicators.dropna(subset=["close"]).iloc[-1] if not indicators.dropna(subset=["close"]).empty else None
    metadata = equity["metadata"]
    data_gaps: list[str] = []

    latest_close = _clean_float(latest_row["close"]) if latest_row is not None else None
    latest_date = str(latest_row.name.date()) if latest_row is not None and hasattr(latest_row.name, "date") else None
    if latest_close is None:
        data_gaps.append("Latest close price unavailable.")

    for key, label in (
        ("current_price", "current price"),
        ("week_52_high", "52-week high"),
        ("week_52_low", "52-week low"),
        ("pe_ratio", "P/E ratio"),
    ):
        if metadata.get(key) is None:
            data_gaps.append(f"{label} unavailable from metadata provider.")

    indicator_summary = snapshot.model_dump(mode="json", exclude_none=True)
    return (
        PriceDataResult(
            ticker=ticker.upper(),
            company_name=metadata.get("company_name"),
            current_price=_clean_float(metadata.get("current_price")),
            week_52_high=_clean_float(metadata.get("week_52_high")),
            week_52_low=_clean_float(metadata.get("week_52_low")),
            pe_ratio=_clean_float(metadata.get("pe_ratio")),
            latest_close=latest_close,
            latest_date=latest_date,
            momentum_signal=snapshot.momentum_signal,
            indicator_summary=indicator_summary,
            data_gaps=data_gaps,
        ),
        indicators,
    )


def calculate_volatility(ticker: str, prices: pd.DataFrame) -> VolatilityResult:
    """Calculate realized volatility for Agent A only."""

    data_gaps: list[str] = []
    if prices.empty or "close" not in prices.columns:
        return VolatilityResult(
            ticker=ticker.upper(),
            summary="Volatility unavailable because close prices were not returned.",
            data_gaps=["Close price history unavailable."],
        )

    close = pd.to_numeric(prices["close"], errors="coerce").dropna()
    returns = close.pct_change().dropna()
    observations = int(returns.shape[0])
    if observations < 30:
        data_gaps.append("Fewer than 30 daily returns available; volatility estimate is weak.")
    if observations == 0:
        return VolatilityResult(
            ticker=ticker.upper(),
            observations=0,
            summary="Volatility unavailable because daily returns could not be computed.",
            data_gaps=data_gaps or ["Daily returns unavailable."],
        )

    daily_vol = float(returns.std())
    annualized_vol = float(daily_vol * math.sqrt(252))
    return VolatilityResult(
        ticker=ticker.upper(),
        daily_volatility=daily_vol,
        annualized_volatility=annualized_vol,
        observations=observations,
        summary=(
            f"Realized annualized volatility is {annualized_vol:.1%} "
            f"from {observations} daily return observations."
        ),
        data_gaps=data_gaps,
    )


def llm_sentiment(ticker: str, headlines: list[str] | None = None) -> SentimentResult:
    """Summarize market sentiment for Agent A without using web search."""

    titles = headlines or []
    if not titles:
        return SentimentResult(
            ticker=ticker.upper(),
            aggregate_label="neutral",
            aggregate_score=0.0,
            data_gaps=["No headlines supplied to Agent A sentiment tool."],
        )

    try:
        client = LLMClient()
        payload, _ = client.generate_json(
            PER_HEADLINE_SENTIMENT_PROMPT,
            "\n".join(f"- {title}" for title in titles[:5]),
            max_tokens=600,
        )
        sentiment = str(payload.get("sentiment", "neutral")).lower()
        confidence = _clean_float(payload.get("confidence")) or 0.5
        score = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}.get(sentiment, 0.0) * confidence
        reason = str(payload.get("brief_reason") or "LLM sentiment summary generated from supplied headlines.")
        return SentimentResult(
            ticker=ticker.upper(),
            aggregate_label=sentiment if sentiment in {"positive", "negative", "neutral"} else "neutral",
            aggregate_score=max(-1.0, min(1.0, score)),
            evidence=[reason],
        )
    except Exception:
        positive_words = {"beat", "growth", "raises", "upgrade", "profit", "record", "strong", "surge"}
        negative_words = {"miss", "risk", "lawsuit", "downgrade", "fall", "weak", "probe", "cut"}
        score = 0
        for title in titles:
            words = set(title.lower().replace(",", " ").split())
            score += int(bool(words & positive_words))
            score -= int(bool(words & negative_words))
        label = "positive" if score > 0 else "negative" if score < 0 else "neutral"
        normalized = max(-1.0, min(1.0, score / max(1, len(titles))))
        return SentimentResult(
            ticker=ticker.upper(),
            aggregate_label=label,
            aggregate_score=normalized,
            evidence=[f"Rule-based fallback sentiment over {len(titles)} supplied headlines."],
        )


def get_news(ticker: str, company_name: str | None = None, min_headlines: int = 5) -> list[NewsHeadline]:
    """Fetch news for Agent B only."""

    return fetch_headlines(ticker, min_headlines=min_headlines, company_name=company_name).headlines


def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web for Agent B only, returning compact evidence records."""

    try:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            from ddgs import DDGS  # type: ignore

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

    results: list[dict[str, str]] = []
    for item in raw_results:
        title = str(item.get("title") or item.get("heading") or "").strip()
        href = str(item.get("href") or item.get("url") or "").strip()
        body = str(item.get("body") or item.get("snippet") or "").strip()
        if title:
            results.append({"title": title, "url": href, "snippet": body})
    return results


def run_data_analyst(ticker: str, session_id: str, seed_headlines: list[str] | None = None) -> AgentDataBrief:
    """Agent A: uses only get_price_data, calculate_volatility, and llm_sentiment."""

    traces: list[AgentToolTrace] = []
    data_gaps: list[str] = []

    start = time.monotonic()
    try:
        price_data, indicators = get_price_data(ticker)
        traces.append(
            _trace_tool(session_id, AGENT_A_NAME, "get_price_data", {"ticker": ticker}, start, price_data.model_dump_json())
        )
    except Exception as exc:
        traces.append(_trace_tool(session_id, AGENT_A_NAME, "get_price_data", {"ticker": ticker}, start, "", "error", str(exc)))
        price_data = PriceDataResult(
            ticker=ticker.upper(),
            data_gaps=[f"Price provider failed: {type(exc).__name__}: {exc}"],
        )
        indicators = pd.DataFrame(columns=["close"])

    start = time.monotonic()
    volatility = calculate_volatility(ticker, indicators)
    traces.append(
        _trace_tool(
            session_id,
            AGENT_A_NAME,
            "calculate_volatility",
            {"ticker": ticker, "price_rows": len(indicators)},
            start,
            volatility.model_dump_json(),
        )
    )

    start = time.monotonic()
    sentiment = llm_sentiment(ticker, seed_headlines)
    traces.append(
        _trace_tool(
            session_id,
            AGENT_A_NAME,
            "llm_sentiment",
            {"ticker": ticker, "headline_count": len(seed_headlines or [])},
            start,
            sentiment.model_dump_json(),
        )
    )

    data_gaps.extend(price_data.data_gaps)
    data_gaps.extend(volatility.data_gaps)
    data_gaps.extend(sentiment.data_gaps)

    price_summary = (
        f"{price_data.ticker} latest close was {_fmt_money(price_data.latest_close)}"
        f"{f' on {price_data.latest_date}' if price_data.latest_date else ''}; "
        f"current metadata price is {_fmt_money(price_data.current_price)}, "
        f"52-week range is {_fmt_money(price_data.week_52_low)} to {_fmt_money(price_data.week_52_high)}, "
        f"and P/E is {_fmt_ratio(price_data.pe_ratio)}."
    )
    sentiment_summary = (
        f"Sentiment is {sentiment.aggregate_label} with score {sentiment.aggregate_score:.2f}. "
        + " ".join(sentiment.evidence[:2])
    )
    notable_signals = [
        f"Momentum signal: {price_data.momentum_signal or 'unavailable'}",
        volatility.summary,
    ]
    if price_data.indicator_summary:
        notable_signals.append(f"Latest indicators: {price_data.indicator_summary}")

    return AgentDataBrief(
        ticker=ticker.upper(),
        price_summary=price_summary,
        volatility_summary=volatility.summary,
        sentiment_summary=sentiment_summary,
        notable_signals=notable_signals,
        tool_traces=traces,
        data_gaps=sorted(set(data_gaps)),
    )


def ask_data_clarification(data_brief: AgentDataBrief) -> str:
    """Agent B asks exactly one specific clarification from Agent A."""

    return (
        "Which single quantitative signal from your brief most changes the hedge recommendation, "
        "and what exact metric supports it?"
    )


def answer_clarification(question: str, data_brief: AgentDataBrief) -> ClarificationAnswer:
    """Agent A answers Agent B with structured data only."""

    volatility_signal = next((signal for signal in data_brief.notable_signals if "volatility" in signal.lower()), None)
    momentum_signal = next((signal for signal in data_brief.notable_signals if "momentum signal" in signal.lower()), None)
    answer = volatility_signal or momentum_signal or data_brief.volatility_summary
    return ClarificationAnswer(
        question=question,
        answer=answer,
        supporting_metrics={
            "price_summary": data_brief.price_summary,
            "volatility_summary": data_brief.volatility_summary,
            "sentiment_summary": data_brief.sentiment_summary,
            "notable_signals": data_brief.notable_signals,
        },
        data_gaps=data_brief.data_gaps,
    )


def run_research_writer(
    data_brief: AgentDataBrief,
    session_id: str,
    clarification: ClarificationAnswer,
) -> tuple[FinalResearchReport, list[AgentToolTrace], dict[str, Any]]:
    """Agent B: uses only get_news and web_search, then writes the final report."""

    traces: list[AgentToolTrace] = []
    ticker = data_brief.ticker

    start = time.monotonic()
    news = get_news(ticker, min_headlines=5)
    traces.append(
        _trace_tool(
            session_id,
            AGENT_B_NAME,
            "get_news",
            {"ticker": ticker, "min_headlines": 5},
            start,
            "; ".join(_headline_titles(news)[:5]),
        )
    )

    start = time.monotonic()
    search_results = web_search(f"{ticker} stock risks hedge strategy recent financial news", max_results=5)
    traces.append(
        _trace_tool(
            session_id,
            AGENT_B_NAME,
            "web_search",
            {"query": f"{ticker} stock risks hedge strategy recent financial news"},
            start,
            "; ".join(result["title"] for result in search_results[:5]),
        )
    )

    news_evidence = _headline_titles(news)[:5]
    search_evidence = [item["title"] for item in search_results[:5]]
    evidence = news_evidence + search_evidence
    if not evidence:
        evidence = ["No external qualitative evidence was returned; report relies on Agent A's structured data brief."]

    risks = [
        f"Market volatility risk: {clarification.answer}",
        f"News and narrative risk: {news_evidence[0] if news_evidence else 'limited current news evidence was available.'}",
        f"Data completeness risk: {data_brief.data_gaps[0] if data_brief.data_gaps else 'no major data gaps were flagged by Agent A.'}",
    ]

    report = FinalResearchReport(
        ticker=ticker,
        generated_at=datetime.utcnow(),
        financial_health_summary=(
            f"{data_brief.price_summary} {data_brief.volatility_summary} "
            f"{data_brief.sentiment_summary} Agent A clarified that {clarification.answer}"
        ),
        top_three_risks=risks[:3],
        hedge_strategy_recommendation=(
            "Use a staged protective-put or collar hedge sized to portfolio exposure. "
            "The hedge is justified by Agent A's volatility clarification and should be revisited "
            "as price, realized volatility, and fresh news evidence change."
        ),
        supporting_evidence=evidence[:10],
        limitations=data_brief.data_gaps,
    )
    metadata = {"news": news, "search_results": search_results}
    return report, traces, metadata


def render_report(report: FinalResearchReport) -> str:
    """Render the final report with the required section headings."""

    risks = "\n".join(f"{idx}. {risk}" for idx, risk in enumerate(report.top_three_risks, start=1))
    evidence = "\n".join(f"- {item}" for item in report.supporting_evidence)
    limitations = "\n".join(f"- {item}" for item in report.limitations) if report.limitations else "- None flagged."
    return (
        f"# {report.ticker} Research Report\n\n"
        "## Financial Health Summary\n"
        f"{report.financial_health_summary}\n\n"
        "## Top Three Risks with supporting evidence\n"
        f"{risks}\n\n"
        "Supporting evidence:\n"
        f"{evidence}\n\n"
        "## Hedge Strategy Recommendation\n"
        f"{report.hedge_strategy_recommendation}\n\n"
        "## Limitations\n"
        f"{limitations}"
    )
