from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

from task3_agentic.src.memory import (
    answer_follow_up_from_state,
    cache_path,
    load_cached_report,
    normalize_ticker,
    save_cached_report,
)
from task3_agentic.src.tools import calculate_volatility, get_news, get_price_data, llm_sentiment, web_search


class AgentState(TypedDict, total=False):
    ticker: str
    run_date: str
    price_data: dict[str, Any]
    price_data_summary: dict[str, Any]
    volatility: dict[str, Any]
    sentiment: dict[str, Any]
    data_brief: str
    news: dict[str, Any]
    web_context: dict[str, Any]
    final_report: str
    agent_a_handoff: dict[str, Any]
    agent_b_critique_request: str
    agent_a_clarification_response: str
    trace_events: list[dict[str, Any]]
    loaded_from_cache: bool
    cache_path: str
    warnings: list[str]


def run_single_agent_research_flow(
    ticker: str,
    period: str = "6mo",
    news_count: int = 6,
    run_date: str | None = None,
    use_cache: bool = True,
) -> AgentState:
    state = _initial_state(ticker, run_date)
    cached = load_cached_report(state["ticker"], state["run_date"]) if use_cache else None
    if cached is not None:
        print("Loaded from cache")
        return _state_from_cache(cached)

    _observe(state, "plan", "Single-agent flow will collect prices, volatility, news, sentiment, and web context.")
    _collect_market_memory(state, period=period, news_count=news_count)
    state["final_report"] = _compose_final_report(state)
    state["cache_path"] = str(save_cached_report(state))
    _observe(state, "cache_save", f"Saved daily report cache to {state['cache_path']}.")
    return state


def run_two_agent_pipeline(
    ticker: str,
    period: str = "6mo",
    news_count: int = 6,
    run_date: str | None = None,
    use_cache: bool = True,
) -> AgentState:
    state = _initial_state(ticker, run_date)
    cached = load_cached_report(state["ticker"], state["run_date"]) if use_cache else None
    if cached is not None:
        print("Loaded from cache")
        return _state_from_cache(cached)

    _observe(state, "plan", "Agent A will prepare quantitative memory; Agent B will critique and write the report.")
    _agent_a_quantitative_brief(state, period=period)
    _agent_b_qualitative_review(state, news_count=news_count)
    _agent_a_clarification(state)
    state["final_report"] = _compose_final_report(state)
    state["cache_path"] = str(save_cached_report(state))
    _observe(state, "cache_save", f"Saved daily report cache to {state['cache_path']}.")
    return state


def ask_follow_up(state: AgentState, question: str) -> str:
    return answer_follow_up_from_state(dict(state), question)


def _initial_state(ticker: str, run_date: str | None) -> AgentState:
    symbol = normalize_ticker(ticker)
    return AgentState(
        ticker=symbol,
        run_date=run_date or date.today().isoformat(),
        trace_events=[],
        warnings=[],
        loaded_from_cache=False,
    )


def _state_from_cache(cached: dict[str, Any]) -> AgentState:
    state = AgentState(**cached)
    state["loaded_from_cache"] = True
    state["cache_path"] = str(cache_path(state["ticker"], state["run_date"]))
    state.setdefault("trace_events", [])
    _observe(state, "cache_load", "Loaded from cache; skipped price, news, volatility, sentiment, and web-search tools.")
    return state


def _collect_market_memory(state: AgentState, period: str, news_count: int) -> None:
    _agent_a_quantitative_brief(state, period=period)
    _agent_b_qualitative_review(state, news_count=news_count)
    _agent_a_clarification(state)


def _agent_a_quantitative_brief(state: AgentState, period: str) -> None:
    ticker = state["ticker"]
    price_result = get_price_data(ticker, period)
    volatility_result = calculate_volatility(ticker, window=30)
    state["price_data"] = price_result.data or {}
    state["price_data_summary"] = _price_summary(price_result.data or {}, period)
    state["volatility"] = volatility_result.data or {}
    _record_tool_warning(state, price_result.tool_name, price_result.status, price_result.error)
    _record_tool_warning(state, volatility_result.tool_name, volatility_result.status, volatility_result.error)
    state["data_brief"] = _build_data_brief(state)
    state["agent_a_handoff"] = {
        "ticker": ticker,
        "price_data_summary": state["price_data_summary"],
        "volatility": state["volatility"],
        "data_brief": state["data_brief"],
    }
    _observe(state, "agent_a_handoff", "Agent A produced structured price and volatility memory.")


def _agent_b_qualitative_review(state: AgentState, news_count: int) -> None:
    ticker = state["ticker"]
    news_result = get_news(ticker, news_count)
    state["news"] = news_result.data or {}
    _record_tool_warning(state, news_result.tool_name, news_result.status, news_result.error)

    headlines = [item.get("title", "") for item in state["news"].get("headlines", []) if item.get("title")]
    sentiment_result = llm_sentiment(headlines) if headlines else None
    if sentiment_result is None or sentiment_result.status == "error":
        state["sentiment"] = _fallback_sentiment(headlines)
        if sentiment_result is not None:
            _record_tool_warning(state, sentiment_result.tool_name, sentiment_result.status, sentiment_result.error)
    else:
        state["sentiment"] = sentiment_result.data or {}

    search_result = web_search(f"{ticker} stock analyst outlook")
    state["web_context"] = search_result.data or {}
    _record_tool_warning(state, search_result.tool_name, search_result.status, search_result.error)
    state["agent_b_critique_request"] = (
        "Please clarify whether the price trend and volatility support the qualitative news signal before the final report."
    )
    _observe(state, "agent_b_critique", "Agent B stored news, sentiment, web context, and a critique request.")


def _agent_a_clarification(state: AgentState) -> None:
    latest = state.get("price_data_summary", {}).get("latest_close")
    annualized = state.get("volatility", {}).get("annualized_volatility")
    annualized_text = f"{annualized:.2%}" if isinstance(annualized, (int, float)) else "unavailable"
    state["agent_a_clarification_response"] = (
        f"Latest close is {latest}; 30-day annualized volatility is {annualized_text}. "
        "Treat the report as research context, not investment advice."
    )
    _observe(state, "agent_a_clarification", "Agent A answered Agent B using short-term memory.")


def _price_summary(data: dict[str, Any], period: str) -> dict[str, Any]:
    prices = data.get("prices") or []
    first_close = _first_close(prices)
    latest_close = data.get("latest_close")
    change_pct = None
    if isinstance(first_close, (int, float)) and isinstance(latest_close, (int, float)) and first_close:
        change_pct = (latest_close - first_close) / first_close
    return {
        "ticker": data.get("ticker"),
        "period": period,
        "rows": data.get("rows", 0),
        "latest_close": latest_close,
        "first_close_in_memory": first_close,
        "period_change_pct": change_pct,
    }


def _first_close(prices: list[dict[str, Any]]) -> float | None:
    for row in prices:
        close = row.get("close")
        if isinstance(close, (int, float)):
            return float(close)
    return None


def _build_data_brief(state: AgentState) -> str:
    summary = state.get("price_data_summary", {})
    vol = state.get("volatility", {})
    change = summary.get("period_change_pct")
    change_text = f"{change:.2%}" if isinstance(change, (int, float)) else "unavailable"
    annualized = vol.get("annualized_volatility")
    vol_text = f"{annualized:.2%}" if isinstance(annualized, (int, float)) else "unavailable"
    return (
        f"{state['ticker']} price memory covers {summary.get('rows', 0)} rows for {summary.get('period')}. "
        f"Latest close: {summary.get('latest_close')}. Period change: {change_text}. "
        f"30-day annualized volatility: {vol_text}."
    )


def _compose_final_report(state: AgentState) -> str:
    ticker = state["ticker"]
    summary = state.get("price_data_summary", {})
    sentiment = state.get("sentiment", {})
    news = state.get("news", {})
    warnings = state.get("warnings", [])
    headlines = [item.get("title", "") for item in news.get("headlines", [])[:3]]
    change = summary.get("period_change_pct")
    change_text = f"{change:.2%}" if isinstance(change, (int, float)) else "unavailable"
    annualized = state.get("volatility", {}).get("annualized_volatility")
    vol_text = f"{annualized:.2%}" if isinstance(annualized, (int, float)) else "unavailable"
    sentiment_label = sentiment.get("aggregate_label") or "neutral"

    report = [
        f"# {ticker} Agentic Research Report",
        "",
        f"- Latest close: {summary.get('latest_close')}",
        f"- Period change: {change_text}",
        f"- 30-day annualized volatility: {vol_text}",
        f"- News sentiment: {sentiment_label}",
        "",
        "## Data Brief",
        state.get("data_brief", "No data brief available."),
        "",
        "## Recent Headlines",
    ]
    report.extend(f"- {headline}" for headline in headlines) if headlines else report.append("- No headlines available.")
    report.extend(
        [
            "",
            "## Agent Coordination",
            f"- Agent B critique request: {state.get('agent_b_critique_request', 'Not requested.')}",
            f"- Agent A clarification: {state.get('agent_a_clarification_response', 'No clarification available.')}",
            "",
            "## Research View",
            _research_view(change, annualized, sentiment_label),
            "",
            "This is educational research output only and is not financial advice.",
        ]
    )
    if warnings:
        report.extend(["", "## Warnings"] + [f"- {warning}" for warning in warnings])
    return "\n".join(report)


def _research_view(change: Any, annualized: Any, sentiment_label: str) -> str:
    trend = "positive" if isinstance(change, (int, float)) and change > 0 else "mixed or negative"
    risk = "elevated" if isinstance(annualized, (int, float)) and annualized > 0.35 else "moderate"
    return f"The short-term setup is {trend}, with {risk} volatility and {sentiment_label} news tone."


def _fallback_sentiment(headlines: list[str]) -> dict[str, Any]:
    return {
        "headlines_analyzed": len(headlines),
        "aggregate_label": "neutral",
        "aggregate_score": 0.0,
        "model_name": "local-fallback",
        "sentiments": [
            {"headline": headline, "sentiment": "neutral", "confidence": 0.5, "rationale": "LLM unavailable; neutral fallback."}
            for headline in headlines
        ],
    }


def _record_tool_warning(state: AgentState, tool_name: str, status: str, error: Any) -> None:
    if status == "error":
        message = getattr(error, "message", None) or "unknown error"
        state.setdefault("warnings", []).append(f"{tool_name}: {message}")


def _observe(state: AgentState, event: str, detail: str) -> None:
    state.setdefault("trace_events", []).append({"event": event, "detail": detail})
