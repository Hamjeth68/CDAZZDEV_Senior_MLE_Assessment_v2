# CDAZZDEV Senior MLE Assessment

## Project Overview
This repository implements two assessment tracks:

- **Task 1:** Financial AI equity research assistant.
- **Task 3:** Agentic financial research workflow with tool use, short-term memory, persistent cache, multi-agent handoff, and JSONL observability.

The code is organized so deterministic market-data work is separated from LLM-driven reasoning. Shared modules under `shared/` provide reusable finance data access, news retrieval, LLM provider failover, prompts, schemas, and logging.

## Architecture Overview
- `task1_financial/` fetches OHLCV data, computes indicators, retrieves headlines, runs LLM sentiment/recommendation steps, and renders Markdown/HTML/PNG outputs.
- `task3_agentic/` runs a stateful research graph. Agent A owns quantitative price/volatility memory; Agent B owns news, sentiment, critique, and final synthesis. `src/memory.py` provides short-term follow-up answers and a persistent JSON cache keyed by `{ticker}_{YYYY-MM-DD}`.
- `task3_agentic/logs/agent_trace.jsonl` records tool, cache load, and cache save events.

## Windows Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set at least one provider key in `.env`:

```powershell
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
```

No populated `.env` file should be committed.

## How To Run Notebooks
Start Jupyter from the repository root, then run all cells:

```powershell
jupyter notebook
```

- Task 1 notebook: `task1_financial/task1_equity_research.ipynb`
- Task 3 notebook: `task3_agentic/task3_agentic_research.ipynb`

## Outputs
- Task 1 reports: `task1_financial/outputs/`
- Task 3 cache files: `task3_agentic/cache/{TICKER}_{YYYY-MM-DD}.json`
- Task 3 trace file: `task3_agentic/logs/agent_trace.jsonl`

## Submission Checklist
- [x] Task 1 attempted.
- [x] Task 3 attempted.
- [x] Notebooks include visible outputs.
- [x] Task 3 short-term memory follow-up implemented.
- [x] Task 3 persistent JSON cache implemented.
- [x] Cache load/save events logged.
- [x] `agent_trace.jsonl` generated.
- [x] `CITATIONS.md` and `REFLECTION.md` finalized.
- [x] No secrets committed.

## Video Walkthrough
Placeholder: add unlisted walkthrough URL here before final submission.
