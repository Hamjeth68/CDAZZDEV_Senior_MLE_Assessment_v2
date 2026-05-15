from __future__ import annotations

from datetime import datetime
from typing import Any

from task3_agentic.src.tools import calculate_volatility, get_news, get_price_data, llm_sentiment, web_search


def run_quant_agent(ticker: str, period: str = "2y", volatility_window: int = 30) -> dict[str, Any]:
    """Agent A: use only quantitative tools and return a compact data brief."""
    symbol = ticker.strip().upper()
    price_result = get_price_data(symbol, period)
    volatility_result = calculate_volatility(symbol, volatility_window)

    price_data = price_result.data or {}
    volatility_data = volatility_result.data or {}
    latest_close = price_data.get("latest_close")
    annualized_volatility = volatility_data.get("annualized_volatility")

    notable_signals: list[str] = []
    if latest_close is not None:
        notable_signals.append(f"Latest close is {latest_close:.2f}.")
    if annualized_volatility is not None:
        notable_signals.append(f"Annualized {volatility_window}-day volatility is {annualized_volatility:.2%}.")

    data_gaps = _tool_gaps([price_result, volatility_result])
    return {
        "agent": "agent_a_quant",
        "ticker": symbol,
        "price_result": price_result.model_dump(mode="json"),
        "volatility_result": volatility_result.model_dump(mode="json"),
        "price_summary": _price_summary(price_data, price_result.status),
        "volatility_summary": _volatility_summary(volatility_data, volatility_result.status),
        "notable_signals": notable_signals,
        "data_gaps": data_gaps,
    }


def run_research_agent(ticker: str, quant_brief: dict[str, Any], news_count: int = 8) -> dict[str, Any]:
    """Agent B: use qualitative tools and synthesize the final report."""
    symbol = ticker.strip().upper()
    news_result = get_news(symbol, news_count)
    headlines = [
        item.get("title", "")
        for item in (news_result.data or {}).get("headlines", [])
        if isinstance(item, dict) and item.get("title")
    ]
    sentiment_result = llm_sentiment(headlines) if headlines else _skipped_tool("llm_sentiment", "No headlines available")
    search_result = web_search(f"{symbol} stock analyst outlook risks")

    data_gaps = list(quant_brief.get("data_gaps", []))
    data_gaps.extend(_tool_gaps([news_result, sentiment_result, search_result]))
    final_report = build_final_report(
        symbol,
        quant_brief,
        news_result.model_dump(mode="json"),
        sentiment_result.model_dump(mode="json"),
        search_result.model_dump(mode="json"),
        data_gaps,
    )

    return {
        "agent": "agent_b_research",
        "ticker": symbol,
        "news_result": news_result.model_dump(mode="json"),
        "sentiment_result": sentiment_result.model_dump(mode="json"),
        "search_result": search_result.model_dump(mode="json"),
        "final_report": final_report,
        "data_gaps": data_gaps,
    }


def build_final_report(
    ticker: str,
    quant_brief: dict[str, Any],
    news_result: dict[str, Any],
    sentiment_result: dict[str, Any],
    search_result: dict[str, Any],
    data_gaps: list[str],
) -> str:
    """Create a concise final report from both agents' outputs."""
    news_data = news_result.get("data") or {}
    sentiment_data = sentiment_result.get("data") or {}
    search_data = search_result.get("data") or {}
    headlines = news_data.get("headlines", [])
    snippets = search_data.get("snippets", [])

    risks = _top_risks(quant_brief, sentiment_data, data_gaps)
    recommendation = _recommendation(quant_brief, sentiment_data, data_gaps)
    lines = [
        f"# Agentic Financial Research Report: {ticker}",
        "",
        f"Generated at: {datetime.utcnow().isoformat()} UTC",
        "",
        "## Quantitative Brief",
        quant_brief.get("price_summary", "Price data unavailable."),
        quant_brief.get("volatility_summary", "Volatility data unavailable."),
        "",
        "## Sentiment and Market Narrative",
        _sentiment_summary(sentiment_data, sentiment_result.get("status")),
        _headline_summary(headlines),
        _search_summary(snippets),
        "",
        "## Recommendation",
        recommendation,
        "",
        "## Top Risks",
        *[f"- {risk}" for risk in risks],
        "",
        "## Data Gaps and Limitations",
        *[f"- {gap}" for gap in (data_gaps or ["No material tool failures recorded."])],
    ]
    return "\n".join(lines)


def _price_summary(data: dict[str, Any], status: str) -> str:
    if status != "success":
        return "Price data unavailable from the quantitative tool."
    return f"Fetched {data.get('rows', 0)} price rows; latest close is {data.get('latest_close', 'unknown')}."


def _volatility_summary(data: dict[str, Any], status: str) -> str:
    if status != "success":
        return "Volatility calculation unavailable."
    annualized = data.get("annualized_volatility")
    if annualized is None:
        return f"Volatility window had {data.get('observations', 0)} return observations but no latest estimate."
    return f"Latest annualized volatility over a {data.get('window')}-day window is {annualized:.2%}."


def _sentiment_summary(data: dict[str, Any], status: str) -> str:
    if status != "success":
        return "LLM sentiment was unavailable, so the narrative view is limited."
    label = data.get("aggregate_label") or "unknown"
    score = data.get("aggregate_score")
    return f"Aggregate headline sentiment is {label} with score {score} across {data.get('headlines_analyzed', 0)} headlines."


def _headline_summary(headlines: list[dict[str, Any]]) -> str:
    titles = [item.get("title") for item in headlines[:3] if isinstance(item, dict) and item.get("title")]
    if not titles:
        return "No live headlines were available."
    return "Recent headlines include: " + "; ".join(titles) + "."


def _search_summary(snippets: list[dict[str, Any]]) -> str:
    titles = [item.get("title") for item in snippets[:2] if isinstance(item, dict) and item.get("title")]
    if not titles:
        return "External analyst-search snippets were unavailable."
    return "External context found: " + "; ".join(titles) + "."


def _recommendation(quant_brief: dict[str, Any], sentiment_data: dict[str, Any], data_gaps: list[str]) -> str:
    label = sentiment_data.get("aggregate_label")
    if data_gaps:
        return "Hold / watchlist. Important data or LLM steps were incomplete, so avoid a high-conviction call."
    if label == "positive":
        return "Constructive Hold. Positive sentiment supports monitoring for confirmation from fundamentals and price trend."
    if label == "negative":
        return "Defensive Hold. Negative sentiment argues for caution until the risk narrative improves."
    return "Neutral Hold. Signals are mixed or insufficient for a directional Buy/Sell view."


def _top_risks(quant_brief: dict[str, Any], sentiment_data: dict[str, Any], data_gaps: list[str]) -> list[str]:
    risks = [
        "Market data, news retrieval, and search sources may be delayed or incomplete.",
        "LLM sentiment and synthesis can miss article nuance, timing, and source credibility.",
    ]
    if data_gaps:
        risks.insert(0, "One or more tools failed, reducing confidence in the final synthesis.")
    if sentiment_data.get("aggregate_label") == "negative":
        risks.append("Recent headline sentiment is negative and may pressure near-term interpretation.")
    return risks[:3]


def _tool_gaps(results: list[Any]) -> list[str]:
    gaps = []
    for result in results:
        if getattr(result, "status", None) == "error" and result.error is not None:
            gaps.append(f"{result.tool_name} failed: {result.error.error_type}: {result.error.message}")
    return gaps


def _skipped_tool(tool_name: str, message: str) -> Any:
    from task3_agentic.src.schemas import ToolError, ToolResult

    return ToolResult(status="error", tool_name=tool_name, error=ToolError(error_type="Skipped", message=message))
