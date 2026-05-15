from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from task3_agentic.src.agents import run_quant_agent, run_research_agent
from task3_agentic.src.memory import load_cached_report, save_cached_report

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def run_two_agent_pipeline(
    ticker: str,
    period: str = "2y",
    news_count: int = 8,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Run the Task 3 two-agent research workflow.

    The implementation is intentionally dependency-light: it preserves the
    assessment's two-agent/tool-restriction shape without requiring LangGraph to
    be installed in the base environment.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker must be a non-empty symbol")

    if use_cache:
        cached = load_cached_report(symbol)
        if cached is not None:
            cached["cache_hit"] = True
            return cached

    quant_brief = run_quant_agent(symbol, period=period)
    research_brief = run_research_agent(symbol, quant_brief, news_count=news_count)
    final_report = research_brief["final_report"]
    output_path = _write_report(symbol, final_report)

    payload = {
        "ticker": symbol,
        "generated_at": datetime.utcnow().isoformat(),
        "cache_hit": False,
        "quant_brief": quant_brief,
        "research_brief": research_brief,
        "final_report": final_report,
        "output_path": str(output_path),
        "warnings": research_brief.get("data_gaps", []),
    }
    save_cached_report(symbol, payload)
    return payload


def _write_report(ticker: str, final_report: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{ticker}_agentic_report.md"
    path.write_text(final_report, encoding="utf-8")
    return path
