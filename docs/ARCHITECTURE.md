# Architecture Diagrams

These diagrams show the main system, task-level data flows, and the optional cloud deployment shape for the assessment.

## 1. Repository-Level System Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CDAZZDEV Senior MLE Assessment                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐     ┌────────────────────┐     ┌──────────────────┐ │
│  │ Task 1 Notebook    │     │ Task 2 Scripts      │     │ Task 3 Notebook  │ │
│  │ Equity Research    │     │ HF Fine-Tuning      │     │ Agentic Research │ │
│  └─────────┬──────────┘     └─────────┬──────────┘     └────────┬─────────┘ │
│            │                          │                         │           │
│  ┌─────────▼──────────┐     ┌─────────▼──────────┐     ┌────────▼─────────┐ │
│  │ task1_financial/   │     │ task2_finetuning/   │     │ task3_agentic/   │ │
│  │ - pipeline         │     │ - train             │     │ - tools          │ │
│  │ - sentiment        │     │ - predict           │     │ - schemas        │ │
│  │ - recommendation   │     │ - upload            │     │ - observability  │ │
│  │ - reports          │     │ - model artifacts   │     │ - cache/logs     │ │
│  └─────────┬──────────┘     └─────────┬──────────┘     └────────┬─────────┘ │
│            │                          │                         │           │
│            └──────────────┬───────────┴───────────┬─────────────┘           │
│                           │                       │                         │
│                  ┌────────▼───────────────────────▼────────┐                │
│                  │ shared/                                 │                │
│                  │ - config and provider keys              │                │
│                  │ - yfinance market data                  │                │
│                  │ - news retrieval with fallback          │                │
│                  │ - indicators                            │                │
│                  │ - prompts and Pydantic schemas          │                │
│                  │ - LLM client with provider failover     │                │
│                  │ - structured logging                    │                │
│                  └────────┬───────────────────────┬────────┘                │
│                           │                       │                         │
│        ┌──────────────────▼─────┐       ┌─────────▼─────────────────┐       │
│        │ External Data Sources   │       │ External Model Providers   │       │
│        │ - yfinance OHLCV/news   │       │ - Groq primary             │       │
│        │ - DuckDuckGo fallback   │       │ - OpenRouter fallback      │       │
│        │ - user CSV data         │       │ - Hugging Face Hub         │       │
│        └────────────────────────┘       └───────────────────────────┘       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 2. Task 1: Equity Research Pipeline

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                      Task 1: Financial AI Research Assistant                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                                                            │
│  │ User Ticker  │                                                            │
│  │ e.g. MSFT    │                                                            │
│  └──────┬───────┘                                                            │
│         │                                                                    │
│  ┌──────▼───────────────────────────────────────────────────────────────┐     │
│  │ run_equity_research()                                                │     │
│  │ task1_financial/src/pipeline.py                                      │     │
│  └──────┬─────────────────────┬─────────────────────┬──────────────────┘     │
│         │                     │                     │                        │
│  ┌──────▼───────┐      ┌──────▼────────┐     ┌──────▼────────┐              │
│  │ OHLCV + Meta │      │ News Headlines │     │ Indicators    │              │
│  │ yfinance     │      │ yf + DDG       │     │ RSI/MACD/SMA  │              │
│  └──────┬───────┘      └──────┬────────┘     └──────┬────────┘              │
│         │                     │                     │                        │
│         │              ┌──────▼─────────────────────┐                        │
│         │              │ LLM Sentiment Service       │                        │
│         │              │ - one headline per call     │                        │
│         │              │ - strict JSON               │                        │
│         │              │ - Pydantic validation       │                        │
│         │              └──────┬─────────────────────┘                        │
│         │                     │                                              │
│         └──────────────┬──────┴─────────────────────┐                        │
│                        │                            │                        │
│                 ┌──────▼────────────────────────────▼──────┐                 │
│                 │ Signal Reasoner                           │                 │
│                 │ - technical snapshot                      │                 │
│                 │ - aggregate sentiment                     │                 │
│                 │ - Buy/Hold/Sell JSON recommendation       │                 │
│                 │ - conservative Hold fallback              │                 │
│                 └──────┬────────────────────────────┬──────┘                 │
│                        │                            │                        │
│          ┌─────────────▼────────────┐    ┌──────────▼───────────┐            │
│          │ Markdown + HTML Brief     │    │ Price Chart PNG       │            │
│          │ outputs/{TICKER}_brief    │    │ matplotlib artifact   │            │
│          └──────────────────────────┘    └──────────────────────┘            │
│                                                                              │
│  Non-fatal failures are collected in warnings and surfaced in the result.     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 3. Shared LLM Provider Failover

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Shared LLM Client Flow                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────┐                                                   │
│  │ Prompt + JSON Contract │                                                   │
│  └───────────┬───────────┘                                                   │
│              │                                                               │
│  ┌───────────▼───────────┐                                                   │
│  │ LLMClient             │                                                   │
│  │ - configured keys     │                                                   │
│  │ - retries             │                                                   │
│  │ - JSON parsing        │                                                   │
│  └───────────┬───────────┘                                                   │
│              │                                                               │
│       ┌──────▼──────┐                                                        │
│       │ Groq Primary │                                                        │
│       └──────┬──────┘                                                        │
│              │ success                                                       │
│              ▼                                                               │
│       ┌─────────────┐        failure/rate limit/auth/provider error          │
│       │ JSON Result │ ◄──────────────────────────────────────────────┐        │
│       └──────┬──────┘                                                │        │
│              │                                                       │        │
│              │                                         ┌─────────────▼──────┐ │
│              │                                         │ OpenRouter Fallback │ │
│              │                                         └─────────────┬──────┘ │
│              │                                                       │        │
│       ┌──────▼───────────────────────────────────────────────────────▼──────┐ │
│       │ Pydantic Validation + Structured Warnings/Errors                    │ │
│       └─────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 4. Task 2: Hugging Face Fine-Tuning Workflow

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                     Task 2: Financial Sentiment Fine-Tuning                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────┐                                            │
│  │ financial_headlines_sample.csv│                                            │
│  │ text,label                    │                                            │
│  └──────────────┬───────────────┘                                            │
│                 │                                                            │
│  ┌──────────────▼───────────────┐                                            │
│  │ Load + Validate Labels        │                                            │
│  │ positive/neutral/negative     │                                            │
│  └──────────────┬───────────────┘                                            │
│                 │                                                            │
│  ┌──────────────▼───────────────┐                                            │
│  │ Stratified Train/Eval Split   │                                            │
│  └──────────────┬───────────────┘                                            │
│                 │                                                            │
│      ┌──────────▼───────────┐       ┌───────────────────────────────┐        │
│      │ AutoTokenizer        │       │ AutoModelForSequenceClassif.   │        │
│      │ distilbert-base      │       │ 3 labels                       │        │
│      └──────────┬───────────┘       └───────────────┬───────────────┘        │
│                 │                                   │                        │
│                 └──────────────┬────────────────────┘                        │
│                                │                                             │
│                       ┌────────▼────────┐                                    │
│                       │ HF Trainer       │                                    │
│                       │ - train          │                                    │
│                       │ - evaluate       │                                    │
│                       │ - macro F1       │                                    │
│                       │ - accuracy       │                                    │
│                       └────────┬────────┘                                    │
│                                │                                             │
│          ┌─────────────────────▼─────────────────────┐                       │
│          │ task2_finetuning/outputs/                  │                       │
│          │ - financial-sentiment-model/               │                       │
│          │ - tokenizer/model config                   │                       │
│          │ - eval_metrics.json                        │                       │
│          └──────────────┬────────────────────────────┘                       │
│                         │                                                    │
│        ┌────────────────▼───────────────┐      ┌────────────────────────┐    │
│        │ Local Inference Script          │      │ Optional Hub Upload     │    │
│        │ predict_sentiment.py            │      │ HF_TOKEN / hf auth      │    │
│        └────────────────────────────────┘      └────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 5. Task 3: Agentic Research Workflow

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                     Task 3: Agentic Financial Research                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                                                            │
│  │ User Request │                                                            │
│  │ ticker/query │                                                            │
│  └──────┬───────┘                                                            │
│         │                                                                    │
│  ┌──────▼───────────────────────────────────────────────────────────────┐     │
│  │ Agentic Notebook / Orchestrator                                      │     │
│  │ restricted tool access + typed tool contracts                        │     │
│  └──────┬───────────────┬─────────────────┬─────────────────┬──────────┘     │
│         │               │                 │                 │                │
│  ┌──────▼──────┐ ┌──────▼──────┐  ┌───────▼───────┐ ┌───────▼───────┐       │
│  │ get_price   │ │ get_news    │  │ web_search    │ │ llm_sentiment │       │
│  │ yfinance    │ │ yf + DDG    │  │ analyst refs  │ │ JSON summary  │       │
│  └──────┬──────┘ └──────┬──────┘  └───────┬───────┘ └───────┬───────┘       │
│         │               │                 │                 │                │
│         │        ┌──────▼─────────────────▼──────┐          │                │
│         │        │ calculate_volatility           │          │                │
│         │        │ rolling returns + annualized   │          │                │
│         │        └──────────────┬─────────────────┘          │                │
│         │                       │                            │                │
│         └───────────────────────┼────────────────────────────┘                │
│                                 │                                             │
│                    ┌────────────▼────────────┐                                │
│                    │ Pydantic ToolResult      │                                │
│                    │ success/error envelope   │                                │
│                    └────────────┬────────────┘                                │
│                                 │                                             │
│       ┌─────────────────────────▼───────────────────────────┐                 │
│       │ Observability + Memory                               │                 │
│       │ - logs/agent_trace.jsonl                             │                 │
│       │ - cache/{ticker,date}.json                            │                 │
│       │ - duration, status, inputs, output preview            │                 │
│       └─────────────────────────┬───────────────────────────┘                 │
│                                 │                                             │
│                         ┌───────▼───────┐                                     │
│                         │ Final Report   │                                     │
│                         │ outputs/       │                                     │
│                         └───────────────┘                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 6. Optional Cloud Deployment Shape

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                            AWS / GCP / Azure                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │ CDN / Static │     │ WAF / Auth    │     │ Load Balancer │                 │
│  │ notebook UI  │     │ rate limits   │     │ HTTPS ingress │                 │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                 │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                ┌─────────────▼─────────────┐                                │
│                │ API / Worker Service       │                                │
│                │ FastAPI, batch job, or VM  │                                │
│                └──────┬──────────────┬─────┘                                │
│                       │              │                                      │
│         ┌─────────────▼───┐      ┌───▼─────────────────┐                    │
│         │ Object Storage   │      │ Secrets Manager      │                    │
│         │ reports/charts   │      │ provider/HF tokens   │                    │
│         └─────────────┬───┘      └───┬─────────────────┘                    │
│                       │              │                                      │
│       ┌───────────────▼──────────────▼───────────────┐                      │
│       │ Containerized Python Runtime                  │                      │
│       │ - Task 1 scheduled research jobs              │                      │
│       │ - Task 2 training/inference jobs              │                      │
│       │ - Task 3 agentic workflow jobs                │                      │
│       └───────────────┬──────────────┬───────────────┘                      │
│                       │              │                                      │
│          ┌────────────▼───┐      ┌───▼──────────────┐                       │
│          │ Managed Cache   │      │ Managed Logs      │                       │
│          │ Redis / bucket  │      │ CloudWatch/LogEx  │                       │
│          └────────────┬───┘      └───┬──────────────┘                       │
│                       │              │                                      │
│  ┌────────────────────▼──────────────▼───────────────────────────────┐       │
│  │ External Services                                                   │       │
│  │ yfinance/news/search APIs, Groq, OpenRouter, Hugging Face Hub       │       │
│  └────────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 7. Artifact and Review Flow

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Submission Artifact Flow                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌────────────────┐     ┌────────────────┐             │
│  │ Execute      │     │ Generate        │     │ Validate        │             │
│  │ notebooks    │────►│ outputs/logs    │────►│ tests + review  │             │
│  └──────┬───────┘     └───────┬────────┘     └───────┬────────┘             │
│         │                     │                      │                      │
│  ┌──────▼───────┐     ┌───────▼────────┐     ┌───────▼────────┐             │
│  │ Task 1 brief │     │ Task 2 HF model │     │ Task 3 traces  │             │
│  │ md/html/png  │     │ metrics + URL   │     │ jsonl + cache   │             │
│  └──────┬───────┘     └───────┬────────┘     └───────┬────────┘             │
│         │                     │                      │                      │
│         └─────────────────────┼──────────────────────┘                      │
│                               │                                             │
│                    ┌──────────▼──────────┐                                  │
│                    │ Final Repository     │                                  │
│                    │ README, citations,   │                                  │
│                    │ reflection, diagrams │                                  │
│                    └─────────────────────┘                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```
