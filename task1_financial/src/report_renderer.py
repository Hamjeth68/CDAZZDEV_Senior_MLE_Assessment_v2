"""Markdown, HTML, and chart rendering for Task 1 reports."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from shared.schemas import EquitySummary, LLMRecommendation, NewsHeadline, SentimentBatchResult

DISCLAIMER = (
    "This report is for educational and informational purposes only. "
    "It is not financial advice, investment advice, or a recommendation to trade securities."
)


def save_price_chart(prices: pd.DataFrame, ticker: str, output_dir: str | Path) -> Path | None:
    """Save a matplotlib close-price chart and return the path."""
    if prices is None or prices.empty or "close" not in prices.columns:
        return None

    import matplotlib.pyplot as plt

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    chart_path = output_path / f"{ticker.upper()}_price_chart.png"

    close = pd.to_numeric(prices["close"], errors="coerce").dropna()
    if close.empty:
        return None

    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(close.index, close.values, color="#2563eb", linewidth=1.8, label="Close")
    ax.set_title(f"{ticker.upper()} Close Price")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(chart_path, dpi=150)
    plt.close(fig)
    return chart_path


def render_markdown_brief(
    equity_summary: EquitySummary,
    sentiment: SentimentBatchResult,
    recommendation: LLMRecommendation,
    headlines: list[NewsHeadline],
    chart_path: str | Path | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Generate a concise one-page Markdown research brief."""
    generated_at = generated_at or datetime.utcnow()
    snapshot = equity_summary.indicator_snapshot
    top_headlines = headlines[:3]
    chart_line = f"![Price chart]({Path(chart_path).as_posix()})" if chart_path else "_Price chart unavailable._"

    lines = [
        f"# {equity_summary.ticker} Equity Research Brief",
        f"_Generated {generated_at:%Y-%m-%d %H:%M UTC}_",
        "",
        chart_line,
        "",
        "## Company Snapshot",
        f"- Company: {equity_summary.company_name or equity_summary.ticker}",
        f"- Current price: {_fmt_money(equity_summary.current_price)}",
        f"- 52-week range: {_fmt_money(equity_summary.week_52_low)} - {_fmt_money(equity_summary.week_52_high)}",
        f"- Market cap: {_fmt_large_number(equity_summary.market_cap)}",
        f"- Sector: {equity_summary.sector or 'Unavailable'}",
        f"- P/E ratio: {_fmt_number(equity_summary.pe_ratio)}",
        "",
        "## Technical Outlook",
        f"- Close: {_fmt_money(snapshot.close_price)}",
        f"- SMA 50 / SMA 200: {_fmt_number(snapshot.sma_50)} / {_fmt_number(snapshot.sma_200)}",
        f"- RSI 14: {_fmt_number(snapshot.rsi_14)}",
        f"- MACD / signal: {_fmt_number(snapshot.macd)} / {_fmt_number(snapshot.macd_signal)}",
        f"- Bollinger range: {_fmt_number(snapshot.bollinger_lower)} - {_fmt_number(snapshot.bollinger_upper)}",
        f"- Momentum: {snapshot.momentum_signal or 'Unavailable'}",
        "",
        "## News Sentiment Summary",
        f"- Aggregate: {sentiment.aggregate_label or 'Unavailable'} ({_fmt_number(sentiment.aggregate_score)})",
        f"- Counts: {sentiment.positive_count} positive, {sentiment.neutral_count} neutral, {sentiment.negative_count} negative",
        "",
        "## Top 3 Headlines",
    ]
    if top_headlines:
        lines.extend(f"- {item.title}" for item in top_headlines)
    else:
        lines.append("- No validated headlines available.")

    lines.extend(
        [
            "",
            "## LLM Recommendation",
            f"**{recommendation.recommendation}** with {_fmt_percent(recommendation.confidence)} confidence.",
            "",
            recommendation.rationale,
            "",
            "Key risks: " + ("; ".join(recommendation.key_risks) if recommendation.key_risks else "Unavailable."),
            "",
            "## Risk Disclaimer",
            DISCLAIMER,
            "",
        ]
    )
    return "\n".join(lines)


def render_html_brief(
    equity_summary: EquitySummary,
    sentiment: SentimentBatchResult,
    recommendation: LLMRecommendation,
    headlines: list[NewsHeadline],
    chart_path: str | Path | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Generate a styled single-page HTML research brief."""
    generated_at = generated_at or datetime.utcnow()
    snapshot = equity_summary.indicator_snapshot
    chart_html = (
        f'<img src="{escape(Path(chart_path).name)}" alt="{escape(equity_summary.ticker)} price chart">'
        if chart_path
        else "<p class=\"muted\">Price chart unavailable.</p>"
    )
    headline_items = "".join(f"<li>{escape(item.title)}</li>" for item in headlines[:3]) or "<li>No validated headlines available.</li>"
    risk_items = "".join(f"<li>{escape(risk)}</li>" for risk in recommendation.key_risks) or "<li>Risks unavailable.</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(equity_summary.ticker)} Equity Research Brief</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #111827; background: #f8fafc; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 32px 20px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 30px; }}
    h2 {{ font-size: 18px; color: #1f2937; border-bottom: 1px solid #d1d5db; padding-bottom: 6px; }}
    section {{ margin-top: 22px; }}
    img {{ width: 100%; max-height: 420px; object-fit: contain; background: white; border: 1px solid #d1d5db; }}
    .meta, .muted {{ color: #6b7280; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px 18px; }}
    .metric {{ background: white; border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 12px; }}
    .label {{ display: block; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
    .rec {{ font-size: 22px; font-weight: 700; color: #0f766e; }}
    .disclaimer {{ background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 12px; }}
  </style>
</head>
<body>
<main>
  <h1>{escape(equity_summary.ticker)} Equity Research Brief</h1>
  <p class="meta">Generated {generated_at:%Y-%m-%d %H:%M UTC}</p>
  {chart_html}

  <section>
    <h2>Company Snapshot</h2>
    <div class="grid">
      {_metric("Company", equity_summary.company_name or equity_summary.ticker)}
      {_metric("Current price", _fmt_money(equity_summary.current_price))}
      {_metric("52-week range", f"{_fmt_money(equity_summary.week_52_low)} - {_fmt_money(equity_summary.week_52_high)}")}
      {_metric("Market cap", _fmt_large_number(equity_summary.market_cap))}
      {_metric("Sector", equity_summary.sector or "Unavailable")}
      {_metric("P/E ratio", _fmt_number(equity_summary.pe_ratio))}
    </div>
  </section>

  <section>
    <h2>Technical Outlook</h2>
    <div class="grid">
      {_metric("Close", _fmt_money(snapshot.close_price))}
      {_metric("SMA 50 / SMA 200", f"{_fmt_number(snapshot.sma_50)} / {_fmt_number(snapshot.sma_200)}")}
      {_metric("RSI 14", _fmt_number(snapshot.rsi_14))}
      {_metric("MACD / signal", f"{_fmt_number(snapshot.macd)} / {_fmt_number(snapshot.macd_signal)}")}
      {_metric("Bollinger range", f"{_fmt_number(snapshot.bollinger_lower)} - {_fmt_number(snapshot.bollinger_upper)}")}
      {_metric("Momentum", snapshot.momentum_signal or "Unavailable")}
    </div>
  </section>

  <section>
    <h2>News Sentiment Summary</h2>
    <p>{escape(sentiment.aggregate_label or "Unavailable")} aggregate sentiment with score {_fmt_number(sentiment.aggregate_score)}.</p>
    <p class="meta">{sentiment.positive_count} positive, {sentiment.neutral_count} neutral, {sentiment.negative_count} negative.</p>
    <ul>{headline_items}</ul>
  </section>

  <section>
    <h2>LLM Recommendation</h2>
    <p class="rec">{escape(recommendation.recommendation)} ({_fmt_percent(recommendation.confidence)} confidence)</p>
    <p>{escape(recommendation.rationale)}</p>
    <ul>{risk_items}</ul>
  </section>

  <section class="disclaimer">
    <h2>Risk Disclaimer</h2>
    <p>{escape(DISCLAIMER)}</p>
  </section>
</main>
</body>
</html>
"""


def write_report_files(
    equity_summary: EquitySummary,
    sentiment: SentimentBatchResult,
    recommendation: LLMRecommendation,
    headlines: list[NewsHeadline],
    prices: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, str | None]:
    """Render chart, Markdown, and HTML files under ``output_dir``."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    ticker = equity_summary.ticker.upper()
    chart_path = save_price_chart(prices, ticker, output_path)

    markdown = render_markdown_brief(equity_summary, sentiment, recommendation, headlines, chart_path)
    html = render_html_brief(equity_summary, sentiment, recommendation, headlines, chart_path)

    md_path = output_path / f"{ticker}_equity_brief.md"
    html_path = output_path / f"{ticker}_equity_brief.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    return {
        "markdown": str(md_path),
        "html": str(html_path),
        "chart": str(chart_path) if chart_path else None,
    }


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span class="label">{escape(label)}</span>{escape(value)}</div>'


def _fmt_money(value: float | None) -> str:
    return "Unavailable" if value is None else f"${value:,.2f}"


def _fmt_number(value: float | None) -> str:
    return "Unavailable" if value is None else f"{value:,.2f}"


def _fmt_percent(value: float | None) -> str:
    return "Unavailable" if value is None else f"{value:.0%}"


def _fmt_large_number(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    for suffix in ("", "K", "M", "B", "T"):
        if abs(value) < 1000.0:
            return f"${value:,.2f}{suffix}"
        value /= 1000.0
    return f"${value:,.2f}Q"

