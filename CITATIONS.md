# CITATIONS.md

## AI Tool Usage
AI assistance was used as a coding accelerator. The final architecture, edge-case behavior, provider choices, and assessment fit were reviewed during integration.

### Repository Scaffold and Documentation
- Tool: ChatGPT/Codex
- Date of assistance: 2026-05-12
- Prompt intent: create initial CDAZZDEV assessment structure and documentation shell.
- Used for: folder layout, README/checklist framing, documentation organization.

### Shared Finance and LLM Foundation
- Tool: ChatGPT/Codex
- Date of assistance: 2026-05-12 to 2026-05-13
- Prompt intent: implement reusable config, schemas, logging, finance data access, news retrieval, and LLM provider abstraction.
- Used for: Pydantic scaffolding, dotenv configuration, provider failover, yfinance normalization, and structured logging.

### Task 1 Financial Research Assistant
- Tool: ChatGPT/Codex
- Date of assistance: 2026-05-13
- Prompt intent: implement Task 1 equity research assistant.
- Used for: pipeline orchestration, LLM sentiment validation, recommendation validation, report rendering, chart generation, and graceful warning paths.

### Task 3 Agentic Tools and Observability
- Tool: ChatGPT/Codex
- Date of assistance: 2026-05-13
- Prompt intent: implement Task 3 tools, schemas, web-search wrapper, and JSONL trace logging.
- Used for: Pydantic tool contracts, append-only `agent_trace.jsonl`, and structured error handling.

### Phase 8 to Phase 10 Completion
- Tool: ChatGPT/Codex
- Date of assistance: 2026-05-14
- Prompt intent: implement short-term memory, persistent JSON cache keyed by ticker/date, cache observability, Task 3 notebook, and final documentation.
- Used for: `task3_agentic/src/memory.py`, reconstructed `task3_agentic/src/graph.py`, notebook section/output generation, README updates, citations update, and reflection finalization.

## Libraries and Documentation Referenced
- Pydantic: https://docs.pydantic.dev/
- python-dotenv: https://pypi.org/project/python-dotenv/
- Requests: https://docs.python-requests.org/
- Groq Python SDK: https://github.com/groq/groq-python
- OpenRouter API: https://openrouter.ai/docs
- yfinance: https://pypi.org/project/yfinance/
- pandas: https://pandas.pydata.org/docs/
- NumPy: https://numpy.org/doc/
- Matplotlib: https://matplotlib.org/stable/users/index.html
- duckduckgo-search: https://pypi.org/project/duckduckgo-search/
- Jupyter Notebook format: https://nbformat.readthedocs.io/

## Adapted Code Sources
No third-party source code was copied directly. Implementations were written specifically for this assessment using public package APIs and documentation.

## Data Sources
- Yahoo Finance market data and company news through `yfinance`.
- DuckDuckGo search/news fallback through `duckduckgo-search`/`ddgs`.
- LLM output from Groq or OpenRouter when local API keys are configured.
