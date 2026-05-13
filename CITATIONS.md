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

### 4) Task 3 Agentic Tools and Observability
- Tool: ChatGPT/Codex
- Date: 2026-05-13
- Prompt intent: implement Task 3 tool wrappers, structured tool schemas,
  DuckDuckGo analyst search, and JSONL observability traces.
- Used for: Pydantic tool result contracts, append-only trace logging,
  structured error handling, and integration with existing shared finance/news/LLM helpers.
- Human work: selected explicit Task 3 schemas, reviewed the plan before implementation,
  and constrained the public tool surface to the five required functions.

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
- duckduckgo-search: https://pypi.org/project/duckduckgo-search/

## Open-Source Code
No source code was copied directly. Implementations were written for this assessment using public API/docs references.

## Data Sources
yfinance/Yahoo Finance market data, accessed through the `yfinance` Python package.
DuckDuckGo search result snippets, accessed through the `duckduckgo-search` Python package.
