# REFLECTION.md

This submission focuses on building a production-oriented financial AI research system rather than a one-off notebook. I designed a shared financial core used by both Task 1 and Task 3 so that OHLCV ingestion, indicator computation, news retrieval, LLM calls, and Pydantic validation are reusable and testable.

For Task 1, the main architectural decision was to separate deterministic financial computation from probabilistic LLM reasoning. Technical indicators are computed from first principles using pandas/numpy, while the LLM is only used for sentiment classification and combined signal reasoning. All LLM outputs are validated using Pydantic so malformed responses do not silently enter the final report.

For Task 3, I selected LangGraph because the assessment requires stateful reasoning, tool invocation, memory, and multi-agent coordination. Agent A is restricted to quantitative tools and produces a structured data brief. Agent B is restricted to qualitative research tools and produces the final report. The critique loop demonstrates that the agents coordinate rather than simply run in a fixed sequence.

The main limitation is reliance on free-tier APIs and public financial/news data. News availability can vary by ticker, so the system includes fallback behavior and graceful degradation. Another limitation is that the recommendation is not investment advice and should not be used for live trading decisions.

With more time, I would add richer fundamental data, SEC filing retrieval, earnings transcript ingestion, LangSmith tracing, and a Streamlit dashboard for reviewing agent traces. I would also expand test coverage around edge cases such as thinly traded tickers, missing PE ratios, failed LLM responses, and empty news results.
