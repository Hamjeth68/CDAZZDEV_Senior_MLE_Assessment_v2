# REFLECTION.md

This submission focuses on a small but production-shaped financial research system rather than a one-off notebook. I separated deterministic computation from probabilistic LLM reasoning: data retrieval, indicators, cache I/O, and tracing are ordinary Python modules, while LLM calls are limited to sentiment and research synthesis paths with validated outputs or conservative fallbacks.

For Task 1, the key architecture decision was to keep the equity pipeline modular. OHLCV data, indicators, news, sentiment, signal reasoning, and rendering each have their own boundary. That makes partial failure easier to handle: if news or an LLM provider is unavailable, the pipeline can still return warnings and the pieces that succeeded.

For Task 3, I used an explicit state graph represented by `AgentState`. Agent A owns quantitative memory such as price summary, volatility, and a structured handoff. Agent B owns news, sentiment, critique request, and final synthesis. Short-term memory enables follow-up answers without tool calls, while the daily JSON cache avoids repeating the same work for the same ticker/date. `agent_trace.jsonl` records tool and cache events for observability.

The main limitation is reliance on free-tier and public data sources. Yahoo Finance and DuckDuckGo can be rate-limited or unavailable, and LLM providers require local keys. The implementation therefore emphasizes graceful degradation, warnings, and cached reuse instead of assuming perfect network access.

With more time, I would add richer fundamentals, SEC filings, earnings transcript retrieval, stronger test coverage for the agent graph, LangSmith-style trace visualization, and a small dashboard for comparing cached runs across tickers. I would also add provider-specific retry budgets so free-tier limits are handled more transparently in notebooks.
