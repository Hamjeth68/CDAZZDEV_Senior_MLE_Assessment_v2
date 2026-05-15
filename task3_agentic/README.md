# Task 3: Agentic Financial Research Workflow

## Objective
Implement a two-agent financial research workflow with restricted tool access, observability traces, and cache-backed memory. The current implementation keeps the orchestration dependency-light in plain Python while preserving the LangGraph-style state flow required by the assessment: Agent A produces a quantitative brief, Agent B uses qualitative tools and writes the final report.

## Structure
- `src/tools.py` - restricted tool functions: price data, volatility, news, LLM sentiment, and web search.
- `src/agents.py` - Agent A quantitative workflow and Agent B research synthesis.
- `src/graph.py` - `run_two_agent_pipeline(...)` entrypoint.
- `src/memory.py` - daily cache helpers under `cache/`.
- `src/observability.py` - JSONL tool traces under `logs/`.
- `src/schemas.py` - Pydantic contracts for tool payloads and traces.
- `logs/` - `agent_trace.jsonl`
- `cache/` - persisted daily report JSON by ticker/date
- `outputs/` - rendered artifacts
- `task3_agentic_research.ipynb` - executed notebook (outputs must remain visible)

## Run
1. Install root requirements.
2. Set at least one LLM provider key in `.env` if you want live sentiment: `GROQ_API_KEY` or `OPENROUTER_API_KEY`.
3. Run the pipeline directly:

```powershell
python -c "from task3_agentic.src.graph import run_two_agent_pipeline; print(run_two_agent_pipeline('MSFT')['final_report'])"
```

4. Or open `task3_agentic_research.ipynb` and execute all cells.
5. Confirm traces, cache behavior, and final report output:

```powershell
type task3_agentic\logs\agent_trace.jsonl
dir task3_agentic\cache
dir task3_agentic\outputs
```

## Outputs
- Return dictionary keys: `ticker`, `generated_at`, `cache_hit`, `quant_brief`, `research_brief`, `final_report`, `output_path`, and `warnings`.
- Markdown report: `outputs/{TICKER}_agentic_report.md`
- Daily cache: `cache/{TICKER}_{YYYY-MM-DD}.json`
- Tool trace log: `logs/agent_trace.jsonl`

## Failure Behavior
Tool failures are captured in typed `ToolResult` envelopes instead of crashing the whole workflow. The final report includes data gaps and limitations when market data, news, search, or LLM calls are unavailable.

If neither `ddgs` nor `duckduckgo-search` is installed, `web_search` returns a successful empty snippet payload instead of failing the agent run. Install root requirements again to enable live search:

```powershell
pip install -r requirements.txt
```
