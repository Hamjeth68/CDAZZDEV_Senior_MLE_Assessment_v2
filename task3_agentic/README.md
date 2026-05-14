# Task 3: Agentic Financial Research Workflow

## Task Objective
Task 3 implements an agentic stock-research workflow with tool use, short-term state memory, persistent daily JSON cache, multi-agent handoff, and append-only observability tracing.

## Rubric Mapping
| Requirement | Implementation |
| --- | --- |
| Tool-using research flow | `src/tools.py` exposes price, volatility, news, sentiment, and web-search tools. |
| Short-term memory | `AgentState` in `src/graph.py` stores ticker, price summary, volatility, sentiment, data brief, news, and final report. |
| Follow-up from memory | `ask_follow_up()` calls `answer_follow_up_from_state()` without re-running tools. |
| Persistent cache | `src/memory.py` saves `cache/{ticker}_{YYYY-MM-DD}.json`. |
| Cache reuse | A second same-day run prints `Loaded from cache` and skips tools. |
| Multi-agent workflow | Agent A produces structured quantitative handoff; Agent B critiques and synthesizes. |
| Observability | `logs/agent_trace.jsonl` records tool and cache events. |

## Files Implemented
- `src/tools.py`
- `src/schemas.py`
- `src/observability.py`
- `src/memory.py`
- `src/graph.py`
- `task3_agentic_research.ipynb`

## How To Run
From the repository root:

```powershell
python -c "from task3_agentic.src.graph import run_two_agent_pipeline; print(run_two_agent_pipeline('MSFT')['final_report'])"
```

Or open `task3_agentic_research.ipynb` and run all cells.

## Expected Outputs
- Daily cache JSON: `task3_agentic/cache/MSFT_{YYYY-MM-DD}.json`
- Trace file: `task3_agentic/logs/agent_trace.jsonl`
- Notebook outputs showing observe/replan trace, Agent A handoff, Agent B critique, short-term follow-up answer, and cache reload message.

## Memory Demonstration
The notebook runs MSFT once to populate short-term memory and persist the final report. It then asks a follow-up question from the returned `AgentState` and runs MSFT again on the same date. The second run prints `Loaded from cache`, proving the persistent cache path skips live tool calls.
