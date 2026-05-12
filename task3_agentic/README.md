# Task 3: Agentic Financial Research Workflow

## Objective
Implement a multi-agent LangGraph workflow with restricted tool access, observability traces, and cache-backed memory.

## Structure
- `src/` - tools, agents, graph, memory, observability
- `logs/` - `agent_trace.jsonl`
- `cache/` - persisted daily report JSON by ticker/date
- `outputs/` - rendered artifacts
- `task3_agentic_research.ipynb` - executed notebook (outputs must remain visible)

## Run
1. Install root requirements.
2. Open `task3_agentic_research.ipynb`.
3. Execute all cells and confirm traces, cache behavior, and final report output.
