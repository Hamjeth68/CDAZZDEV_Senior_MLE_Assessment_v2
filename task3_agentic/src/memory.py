from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

from task3_agentic.src.observability import log_tool_call

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"


def normalize_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker must be a non-empty symbol")
    return symbol


def cache_key(ticker: str, run_date: str | None = None) -> tuple[str, str]:
    symbol = normalize_ticker(ticker)
    resolved_date = run_date or date.today().isoformat()
    return symbol, resolved_date


def cache_path(ticker: str, run_date: str | None = None) -> Path:
    symbol, resolved_date = cache_key(ticker, run_date)
    return CACHE_DIR / f"{symbol}_{resolved_date}.json"


def load_cached_report(ticker: str, run_date: str | None = None) -> dict[str, Any] | None:
    start = time.perf_counter()
    path = cache_path(ticker, run_date)
    inputs = {"ticker": normalize_ticker(ticker), "date": run_date or date.today().isoformat(), "path": str(path)}
    if not path.exists():
        _log_cache_event("cache_load", inputs, {"cache_hit": False}, start)
        return None

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _log_cache_event("cache_load", inputs, {"cache_hit": True, "final_report": payload.get("final_report", "")}, start)
    return payload


def save_cached_report(state: dict[str, Any]) -> Path:
    start = time.perf_counter()
    ticker = normalize_ticker(str(state.get("ticker", "")))
    run_date = str(state.get("run_date") or date.today().isoformat())
    path = cache_path(ticker, run_date)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "ticker": ticker,
        "run_date": run_date,
        "final_report": state.get("final_report"),
        "price_data_summary": state.get("price_data_summary"),
        "volatility": state.get("volatility"),
        "sentiment": state.get("sentiment"),
        "data_brief": state.get("data_brief"),
        "news": state.get("news"),
        "agent_a_handoff": state.get("agent_a_handoff"),
        "agent_b_critique_request": state.get("agent_b_critique_request"),
        "agent_a_clarification_response": state.get("agent_a_clarification_response"),
        "warnings": state.get("warnings", []),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)

    _log_cache_event("cache_save", {"ticker": ticker, "date": run_date, "path": str(path)}, payload, start)
    return path


def answer_follow_up_from_state(state: dict[str, Any], question: str) -> str:
    """Answer a follow-up from in-memory state without calling tools."""
    text = question.casefold()
    ticker = state.get("ticker", "the ticker")

    if "cache" in text:
        source = "cache" if state.get("loaded_from_cache") else "fresh tool run"
        return f"{ticker} was answered from {source}. Cache path: {state.get('cache_path', 'not saved yet')}."
    if "vol" in text or "risk" in text:
        vol = state.get("volatility") or {}
        annualized = vol.get("annualized_volatility")
        if annualized is None:
            return f"I do not have a usable volatility value for {ticker} in short-term memory."
        return f"{ticker} annualized volatility in memory is {annualized:.2%}."
    if "sentiment" in text:
        sentiment = state.get("sentiment") or {}
        label = sentiment.get("aggregate_label") or "unknown"
        score = sentiment.get("aggregate_score")
        suffix = f" with score {score:.2f}" if isinstance(score, (int, float)) else ""
        return f"{ticker} news sentiment in memory is {label}{suffix}."
    if "price" in text or "close" in text:
        summary = state.get("price_data_summary") or {}
        latest = summary.get("latest_close")
        rows = summary.get("rows")
        return f"{ticker} latest close in memory is {latest}; the price summary contains {rows} rows."
    if "news" in text or "headline" in text:
        news = state.get("news") or {}
        headlines = news.get("headlines") or []
        if not headlines:
            return f"No headlines are currently stored in short-term memory for {ticker}."
        titles = [item.get("title", "") for item in headlines[:3]]
        return f"{ticker} headlines in memory include: " + "; ".join(titles)
    if "report" in text or "recommendation" in text:
        report = str(state.get("final_report") or "")
        return report[:900] if report else f"No final report is currently stored in short-term memory for {ticker}."

    return (
        f"I can answer from short-term memory for {ticker}. Available fields: "
        "ticker, price data summary, volatility, sentiment, data brief, news, and final report."
    )


def _log_cache_event(tool_name: str, inputs: dict[str, Any], output: Any, start: float) -> None:
    duration_ms = int((time.perf_counter() - start) * 1000)
    log_tool_call(tool_name=tool_name, inputs=inputs, output=output, duration_ms=duration_ms, status="success")
