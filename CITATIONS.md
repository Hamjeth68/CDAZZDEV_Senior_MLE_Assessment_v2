# CITATIONS.md

## AI Tool Usage

### 1) Repository Scaffold and Documentation
- Tool: ChatGPT/Codex
- Date: 2026-05-12
- Prompt intent: create initial project structure and documentation shell for CDAZZDEV assessment.
- Used for: folder layout, baseline README sections, checklist framing.
- Human edits: normalized wording, tightened setup/run guidance, aligned with rubric language.

### 2) Shared Foundation Modules
- Tool: ChatGPT/Codex
- Date: 2026-05-12
- Prompt intent: generate reusable config/errors/schemas/prompts/logging modules.
- Used for: Pydantic model scaffolding, dotenv loader pattern, prompt centralization.
- Human edits: refined config read behavior, validation boundaries, and logging redaction behavior.

### 3) News Retrieval and LLM Client Abstraction
- Tool: ChatGPT/Codex
- Date: 2026-05-13
- Prompt intent: implement yfinance-first news retrieval and Groq-first LLM abstraction with OpenRouter fallback.
- Used for: provider interface design, retry/failover flow, safe structured logging, headline normalization.
- Human edits: pending review.

## Libraries and Documentation Referenced
- Pydantic: https://docs.pydantic.dev/
- python-dotenv: https://pypi.org/project/python-dotenv/
- Requests: https://docs.python-requests.org/
- Groq Python SDK and chat completions: https://console.groq.com/docs/text-chat
- OpenRouter chat completions API: https://openrouter.ai/docs/api-reference/chat-completion
- yfinance `Ticker.news` / `Ticker.get_news`: https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.news.html and https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_news.html
- duckduckgo-search / DDGS package: https://pypi.org/project/duckduckgo-search/

## Open-Source Code
No source code was copied directly. Implementations were written for this assessment using public API/docs references.

## Data Sources
- Yahoo Finance news via yfinance for ticker-specific headlines.
- DuckDuckGo Search results via duckduckgo-search/DDGS as fallback headline discovery.
