# Task 1: Financial AI Equity Research Assistant

## Objective
Task 1 implements an end-to-end equity research assistant for a single public ticker. It fetches market data, computes technical indicators, retrieves recent news, asks an LLM for structured headline sentiment, asks an LLM for a Buy/Hold/Sell recommendation, and renders a concise Markdown/HTML brief with a matplotlib price chart.

This project is for educational assessment use only. It is not financial advice, investment advice, or a recommendation to buy or sell securities.

## How To Run
Install the root requirements from the repository root:

```bash
pip install -r requirements.txt
```

Set at least one LLM provider key in `.env`. Either provider is enough:

```bash
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
```

Missing optional provider keys are skipped quietly. If no LLM provider is configured, the pipeline records explicit `sentiment_failed` and `recommendation_failed` warnings and falls back to validated empty sentiment / conservative recommendation outputs where possible.

Run the pipeline from the repository root:

```bash
python -c "from task1_financial.src.pipeline import run_equity_research; print(run_equity_research('MSFT'))"
```

Or open `task1_equity_research.ipynb`, choose a ticker, and execute all cells.

## Architecture
- `src/pipeline.py` orchestrates ticker input, OHLCV retrieval, indicator computation, news retrieval, summary construction, LLM calls, report rendering, and graceful partial-failure handling.
- `src/sentiment_service.py` sends each headline to the LLM independently, requires strict JSON, validates with Pydantic, logs validation/provider failures, and propagates provider setup failures so the pipeline can surface warnings.
- `src/signal_reasoner.py` sends the technical snapshot plus aggregate sentiment to the LLM, requires a validated Buy/Hold/Sell response, and propagates provider/validation failures so the pipeline can record the fallback path.
- `src/report_renderer.py` creates a one-page Markdown brief, styled HTML brief, and PNG price chart.
- `shared/` provides reusable schemas, prompts, yfinance data access, indicators, news retrieval, logging, and LLM provider failover.

## Expected Outputs
By default, successful runs write artifacts under `task1_financial/outputs/`:

- `{TICKER}_equity_brief.md`
- `{TICKER}_equity_brief.html`
- `{TICKER}_price_chart.png`

The returned pipeline dictionary includes:

- `equity_summary`: company snapshot plus the latest technical indicator snapshot.
- `sentiment`: validated headline sentiment rows and aggregate counts/score.
- `recommendation`: validated Buy/Hold/Sell recommendation with confidence, rationale, risks, and evidence.
- `headlines`: retrieved news headlines used by the sentiment step.
- `warnings`: non-fatal data, LLM, or rendering issues encountered during the run.

## Notes
External data and LLM services can be unavailable, rate-limited, or incomplete. The pipeline records partial failures in `warnings` and continues wherever possible so the notebook can still show which parts succeeded.
