# Task 1: Financial AI Equity Research Assistant

## Task Objective
Task 1 builds an end-to-end equity research assistant for a single public ticker. It fetches market data, computes technical indicators, retrieves recent headlines, asks an LLM for structured sentiment and Buy/Hold/Sell reasoning, and renders a concise report.

This project is for educational assessment use only. It is not financial advice.

## Rubric Mapping
| Requirement | Implementation |
| --- | --- |
| Market data retrieval | `shared/finance_data.py` uses yfinance for OHLCV and metadata. |
| Technical indicators | `shared/indicators.py` computes indicators with pandas/numpy. |
| LLM sentiment | `src/sentiment_service.py` validates per-headline JSON sentiment. |
| Recommendation reasoning | `src/signal_reasoner.py` validates Buy/Hold/Sell output and falls back safely. |
| Report output | `src/report_renderer.py` writes Markdown, HTML, and PNG chart artifacts. |
| Graceful failure | `src/pipeline.py` records warnings and continues where possible. |

## Files Implemented
- `src/pipeline.py`
- `src/sentiment_service.py`
- `src/signal_reasoner.py`
- `src/report_renderer.py`
- `task1_equity_research.ipynb`

## How To Run
Install requirements from the repository root and set `GROQ_API_KEY` or `OPENROUTER_API_KEY` in `.env`.

```powershell
python -c "from task1_financial.src.pipeline import run_equity_research; print(run_equity_research('MSFT'))"
```

Or open `task1_equity_research.ipynb` and run all cells.

## Expected Outputs
Successful runs write:

- `task1_financial/outputs/{TICKER}_equity_brief.md`
- `task1_financial/outputs/{TICKER}_equity_brief.html`
- `task1_financial/outputs/{TICKER}_price_chart.png`

The notebook displays the equity summary, sentiment table, recommendation, warnings, and generated artifact paths.
