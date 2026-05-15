# REFLECTION.md

This submission focuses on building a production-oriented financial AI research system rather than a one-off notebook. I designed a shared financial core used by Task 1 and Task 3 so that OHLCV ingestion, indicator computation, news retrieval, LLM calls, and Pydantic validation are reusable and testable.

For Task 1, the main architectural decision was to separate deterministic financial computation from probabilistic LLM reasoning. Technical indicators are computed from first principles using pandas/numpy, while the LLM is only used for sentiment classification and combined signal reasoning. All LLM outputs are validated using Pydantic so malformed responses do not silently enter the final report.

For Task 2, I added a lightweight Hugging Face fine-tuning workflow for financial headline sentiment. The implementation uses a small labeled CSV and a DistilBERT sequence-classification pipeline so the experiment is reproducible on CPU and can be uploaded to Hugging Face Hub. The goal is to demonstrate the full MLE workflow: dataset preparation, label mapping, training, evaluation metrics, local inference, and model packaging.

For Task 3, I implemented a dependency-light two-agent orchestration that preserves the LangGraph-style state flow required by the assessment without adding a heavy runtime dependency to the base environment. Agent A is restricted to quantitative tools and produces a structured data brief. Agent B is restricted to qualitative research tools, uses the brief as state, records tool traces, writes a cached final report, and surfaces data gaps rather than hiding tool failures.

The main limitation is reliance on free-tier APIs, public financial/news data, and a small Task 2 sample dataset. News availability can vary by ticker, so the system includes fallback behavior and graceful degradation. The fine-tuned model is a proof of implementation rather than a production-grade classifier. Another limitation is that the recommendation is not investment advice and should not be used for live trading decisions.
