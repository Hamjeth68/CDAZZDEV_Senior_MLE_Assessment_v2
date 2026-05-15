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

### 4) Task 1 Financial AI Equity Research Assistant
- Tool: ChatGPT/Codex
- Date: 2026-05-13
- Prompt intent: implement the Task 1 equity research assistant modules.
- Used for: pipeline orchestration, per-headline JSON sentiment validation,
  Buy/Hold/Sell recommendation validation, Markdown/HTML report rendering,
  matplotlib chart generation, README updates, and graceful partial-failure
  handling.
- Human work: specified the required module boundaries, required the no financial
  advice disclaimer, selected the shared data/LLM abstractions to reuse, and
  reviewed the implementation against the assessment requirements.

### 5) Task 2 Hugging Face Fine-Tuning
- Tool: ChatGPT/Codex
- Date: 2026-05-14
- Prompt intent: add a lightweight Hugging Face fine-tuning workflow for the assessment.
- Used for: Task 2 folder structure, sample financial headline dataset,
  DistilBERT fine-tuning script, inference script, upload instructions, and
  documentation updates.
- Human work: requested the Task 2 attempt, selected a contained classification
  scope, and will create the Hugging Face account/token and upload the trained
  model from the local environment.

### 6) Task 3 Agentic Workflow, Tools, Memory, and Observability
- Tool: ChatGPT/Codex
- Date: 2026-05-13 to 2026-05-15
- Prompt intent: implement Task 3 tool wrappers, structured tool schemas,
  DuckDuckGo analyst search, JSONL observability traces, daily cache memory,
  and the `run_two_agent_pipeline` orchestration entrypoint.
- Used for: Pydantic tool result contracts, append-only trace logging,
  structured error handling, two-agent synthesis structure, local cache helpers,
  and integration with existing shared finance/news/LLM helpers.
- Human work: selected explicit Task 3 schemas, reviewed the plan before implementation,
  constrained the public tool surface to the five required functions, and
  verified that the direct import path works from the project root.

## Human Contributions
- Defined the assessment scope around Task 1, Task 2, and Task 3 rather than building a
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
- Matplotlib: https://matplotlib.org/stable/users/index.html
- duckduckgo-search: https://pypi.org/project/duckduckgo-search/
- Hugging Face Hub user access tokens: https://huggingface.co/docs/hub/main/security-tokens
- Hugging Face Hub CLI login: https://huggingface.co/docs/huggingface_hub/main/guides/cli
- Hugging Face Transformers Trainer: https://huggingface.co/docs/transformers/en/main_classes/trainer
- Hugging Face Datasets: https://huggingface.co/docs/datasets/
- PyTorch: https://pytorch.org/docs/stable/index.html

## Open-Source Code
No source code was copied directly. Implementations were written for this assessment using public API/docs references.

## Data Sources
yfinance/Yahoo Finance market data and company news, accessed through the
`yfinance` Python package. DuckDuckGo search/news is used as a best-effort
headline fallback through `duckduckgo-search`/`ddgs` when yfinance does not
return enough headlines.
DuckDuckGo search result snippets, accessed through the `duckduckgo-search` Python package.
Task 2 uses a small hand-authored sample of financial headline-style examples
for demonstrating the fine-tuning workflow.
