# CITATIONS.md

## AI Tool Usage

AI assistance was used as a coding accelerator, not as a substitute for project
ownership. The final structure, dependency choices, edge-case behavior, and
assessment fit were reviewed and adjusted manually while integrating the code.

### 1) Repository Scaffold and Documentation
- Tool: ChatGPT/Codex
- Date: 2026-05-12
- Prompt intent: create initial project structure and documentation shell for CDAZZDEV assessment.
- Used for: folder layout, baseline README sections, checklist framing.
- Human work: selected the final task layout, removed irrelevant boilerplate,
  tightened setup/run guidance, and aligned the documentation with the
  assessment rubric.

### 2) Shared Foundation Modules
- Tool: ChatGPT/Codex
- Date: 2026-05-12
- Prompt intent: generate reusable config/errors/schemas/prompts/logging modules.
- Used for: Pydantic model scaffolding, dotenv loader pattern, prompt centralization.
- Human work: reviewed schema boundaries, adjusted optional fields for realistic
  missing data, verified secret-redaction behavior, and kept provider config
  simple enough for local notebook use.

### 3) Financial Data and Technical Indicators
- Tool: ChatGPT/Codex
- Date: 2026-05-13
- Prompt intent: implement yfinance-based OHLCV/metadata retrieval and pandas/numpy technical indicators.
- Used for: finance data normalization, SMA/RSI/MACD/Bollinger implementations, lightweight indicator tests.
- Human work: confirmed the indicator formulas against standard definitions,
  required first-principles pandas/numpy implementations instead of TA-Lib,
  chose conservative null handling, and reviewed the tests to avoid dependence
  on live market data.

### 4) LangGraph Multi-Agent Workflow
- Tool: ChatGPT/Codex
- Date: 2026-05-13
- Prompt intent: implement Task 3 LangGraph workflow with restricted tools, structured state, critique loop, and notebook-visible tracing.
- Used for: `AgentState` design, Agent A/Agent B orchestration, Pydantic handoff models, deterministic fallback behavior, and trace rendering.
- Human work: reviewed the required agent boundaries, insisted on no web-search access for Agent A, required the clarification loop to complete without manual input, and verified the final report sections match the assessment brief.

## Human Contributions
- Defined the assessment scope around Task 1 and Task 3 rather than building a
  generic finance app.
- Chose yfinance as the practical data source for reproducible local execution.
- Required relative historical periods such as `period="2y"` so the data layer
  does not age around hardcoded dates.
- Reviewed formula behavior for short histories, flat prices, missing closes,
  and sparse ticker metadata.
- Kept tests lightweight and synthetic so they can run without network access.
- Manually checked project files for merge-marker issues encountered during
  integration.

## Libraries and Documentation Referenced
- Pydantic: https://docs.pydantic.dev/
- python-dotenv: https://pypi.org/project/python-dotenv/
- OpenRouter API: https://openrouter.ai/docs
- Groq SDK: https://github.com/groq/groq-python
- Requests: https://docs.python-requests.org/
- yfinance: https://pypi.org/project/yfinance/
- pandas: https://pandas.pydata.org/docs/
- NumPy: https://numpy.org/doc/
- LangGraph: https://langchain-ai.github.io/langgraph/

## Open-Source Code
No source code was copied directly. Implementations were written for this assessment using public API/docs references.

## Data Sources
yfinance/Yahoo Finance market data, accessed through the `yfinance` Python package.
DuckDuckGo search/news results, accessed through `duckduckgo-search` or `ddgs` when available.
