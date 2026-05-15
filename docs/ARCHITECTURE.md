# Architecture Diagrams

These diagrams describe the current repository shape, task flows, provider behavior, and generated artifacts. They use plain ASCII boxes so they render cleanly in GitHub, notebooks, and terminals.

## 1. Repository-Level System Architecture

```text
+--------------------------------------------------------------------------------+
|                         CDAZZDEV Senior MLE Assessment                         |
+--------------------------------------------------------------------------------+
|                                                                                |
|  +----------------------+     +----------------------+     +------------------+ |
|  | Task 1 Notebook      |     | Task 2 Scripts       |     | Task 3 Notebook  | |
|  | Equity Research      |     | HF Fine-Tuning       |     | Agentic Research | |
|  +----------+-----------+     +----------+-----------+     +---------+--------+ |
|             |                            |                           |          |
|  +----------v-----------+     +----------v-----------+     +---------v--------+ |
|  | task1_financial/     |     | task2_finetuning/    |     | task3_agentic/   | |
|  | - pipeline           |     | - train              |     | - graph          | |
|  | - sentiment          |     | - predict            |     | - agents         | |
|  | - recommendation     |     | - model artifacts    |     | - tools          | |
|  | - reports            |     | - HF upload path     |     | - memory/logs    | |
|  +----------+-----------+     +----------+-----------+     +---------+--------+ |
|             |                            |                           |          |
|             +----------------------------+---------------------------+          |
|                                          |                                      |
|                              +-----------v------------+                         |
|                              | shared/                |                         |
|                              | - config + keys        |                         |
|                              | - yfinance data        |                         |
|                              | - news fallback        |                         |
|                              | - LLM client           |                         |
|                              | - schemas + logging    |                         |
|                              +-----------+------------+                         |
|                                          |                                      |
|                    +---------------------+---------------------+                |
|                    |                                           |                |
|          +---------v----------+                     +----------v----------+     |
|          | External Data      |                     | Model Providers     |     |
|          | - Yahoo/yfinance   |                     | - Groq or           |     |
|          | - DuckDuckGo       |                     | - OpenRouter        |     |
|          | - CSV samples      |                     | - Hugging Face Hub  |     |
|          +--------------------+                     +---------------------+     |
|                                                                                |
+--------------------------------------------------------------------------------+
```

## 2. Shared LLM Provider Behavior

```text
+------------------------+
|       LLMClient()      |
+-----------+------------+
            |
            v
+------------------------+
| Read provider settings |
+-----------+------------+
            |
            v
+-------------------------------+
| Is GROQ_API_KEY configured?   |
+---------------+---------------+
                |
        +-------+-------+
        |               |
      yes              no
        |               |
        v               v
+---------------+   +----------------+
| Build Groq    |   | Skip quietly   |
| provider      |   | no warning     |
+-------+-------+   +--------+-------+
        |                    |
        +----------+---------+
                   |
                   v
+------------------------------------+
| Is OPENROUTER_API_KEY configured? |
+----------------+-------------------+
                 |
         +-------+-------+
         |               |
       yes              no
         |               |
         v               v
+----------------+   +----------------+
| Build          |   | Skip quietly   |
| OpenRouter     |   | no warning     |
+--------+-------+   +--------+-------+
         |                    |
         +----------+---------+
                    |
                    v
+-------------------------------------+
| At least one provider is available? |
+----------------+--------------------+
                 |
          +------+------+
          |             |
        yes            no
          |             |
          v             v
+----------------+   +--------------------------------------------+
| Generate text  |   | raise LLMProviderError                     |
| or JSON        |   | "No LLM providers configured"              |
+-------+--------+   +--------------------------------------------+
        |
        v
+-------------------------------+
| Runtime failure?              |
| log, retry, and fail over     |
| when another provider exists  |
+-------------------------------+
```

## 3. Task 1: Equity Research Pipeline

```text
+------------------------------+
| run_equity_research(ticker)  |
+--------------+---------------+
               |
               v
+------------------------------+        +------------------------------+
| Fetch OHLCV + metadata       |------->| Build EquitySummary          |
| yfinance wrappers            |        | ticker, price, fundamentals  |
+--------------+---------------+        +--------------+---------------+
               |                                       |
               v                                       |
+------------------------------+                       |
| Compute indicators           |                       |
| SMA, RSI, MACD, Bollinger    |                       |
+--------------+---------------+                       |
               |                                       |
               +-------------------+-------------------+
                                   |
                                   v
+------------------------------+        +------------------------------+
| Fetch headlines              |------->| Analyze news sentiment       |
| yfinance + DuckDuckGo        |        | strict JSON + Pydantic       |
+--------------+---------------+        +--------------+---------------+
                                                   |
                                                   v
                                      +------------------------------+
                                      | Generate recommendation      |
                                      | technicals + sentiment       |
                                      +--------------+---------------+
                                                     |
                             +-----------------------+-------------------+
                             |                                           |
                             v                                           v
               +------------------------------+            +------------------------------+
               | Valid LLM recommendation     |            | Fallback recommendation      |
               | Buy/Hold/Sell                |            | conservative validated rule  |
               +--------------+---------------+            +--------------+---------------+
                              |                                           |
                              +-----------------------+-------------------+
                                                      |
                                                      v
                                      +------------------------------+
                                      | Render reports               |
                                      | Markdown, HTML, chart PNG    |
                                      +--------------+---------------+
                                                     |
                                                     v
                                      +------------------------------+
                                      | Return result dictionary     |
                                      | includes visible warnings    |
                                      +------------------------------+
```

Provider and validation failures propagate into the pipeline warning path, so fallback sentiment or recommendation behavior is visible in the returned `warnings` list.

## 4. Task 2: Hugging Face Fine-Tuning Workflow

```text
+------------------------------+
| financial_headlines_sample   |
| CSV labels: pos/neu/neg      |
+--------------+---------------+
               |
               v
+------------------------------+
| train_financial_sentiment.py |
+--------------+---------------+
               |
       +-------+-------+
       |               |
       v               v
+--------------+  +------------------+
| Tokenize     |  | Split train/eval |
| DistilBERT   |  | reproducibly     |
+------+-------+  +--------+---------+
       |                   |
       +---------+---------+
                 |
                 v
+------------------------------+
| Train sequence classifier    |
+--------------+---------------+
               |
       +-------+-------+
       |               |
       v               v
+--------------+  +------------------+
| Save model   |  | eval_metrics.json|
| outputs/     |  | local evidence   |
+------+-------+  +--------+---------+
       |                   |
       +---------+---------+
                 |
                 v
+------------------------------+
| Optional push to HF Hub      |
+------------------------------+
```

Task 2 dependencies live in `task2_finetuning/requirements-task2.txt` so the base Task 1/Task 3 environment stays small.

## 5. Task 3: Agentic Research Workflow

```text
+----------------------------------+
| run_two_agent_pipeline("MSFT")   |
| task3_agentic/src/graph.py       |
+----------------+-----------------+
                 |
                 v
+----------------------------------+
| Check daily cache                |
| cache/MSFT_YYYY-MM-DD.json       |
+----------------+-----------------+
                 |
       +---------+---------+
       |                   |
   cache hit           cache miss
       |                   |
       v                   v
+--------------+   +------------------------------+
| Return cached|   | Agent A: Quantitative        |
| payload      |   | restricted tool access       |
+--------------+   +--------------+---------------+
                                  |
                     +------------+-------------+
                     |                          |
                     v                          v
            +----------------+        +----------------------+
            | get_price_data |        | calculate_volatility |
            +--------+-------+        +----------+-----------+
                     |                           |
                     +-------------+-------------+
                                   |
                                   v
                    +------------------------------+
                    | Quant brief                  |
                    | price + volatility + gaps    |
                    +--------------+---------------+
                                   |
                                   v
                    +------------------------------+
                    | Agent B: Research synthesis  |
                    | qualitative tool access      |
                    +--------------+---------------+
                                   |
             +---------------------+----------------------+
             |                     |                      |
             v                     v                      v
      +-------------+       +---------------+       +---------------+
      | get_news    |       | llm_sentiment |       | web_search    |
      +------+------+       +-------+-------+       +-------+-------+
             |                      |                       |
             +----------------------+-----------------------+
                                    |
                                    v
                    +------------------------------+
                    | Final report Markdown        |
                    | recommendation + limitations |
                    +--------------+---------------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
 +------------------------+ +------------------+ +-------------------------+
 | outputs/MSFT_agentic_  | | cache/MSFT_...   | | logs/agent_trace.jsonl  |
 | report.md              | | .json            | | append-only traces      |
 +------------------------+ +------------------+ +-------------------------+
```

Restricted tool surface:

```text
+-----------------------+----------------------------------------------+
| Tool                  | Purpose                                      |
+-----------------------+----------------------------------------------+
| get_price_data        | yfinance OHLCV payload                       |
| calculate_volatility  | rolling return volatility payload            |
| get_news              | recent headline payload                      |
| llm_sentiment         | structured sentiment over headlines          |
| web_search            | analyst/search snippet payload               |
+-----------------------+----------------------------------------------+
```

Each tool returns a Pydantic `ToolResult` envelope with `status`, `tool_name`, `data`, and `error`.

## 6. Task 3 Memory and Artifact Flow

```text
                  +-----------------------------+
                  | First run for ticker/date   |
                  +--------------+--------------+
                                 |
                                 v
                  +-----------------------------+
                  | Live tool calls             |
                  | traces written as JSONL     |
                  +--------------+--------------+
                                 |
             +-------------------+-------------------+
             |                   |                   |
             v                   v                   v
+----------------------+ +----------------+ +-----------------------------+
| Final Markdown       | | Daily cache    | | Tool trace log              |
| outputs/{TICKER}_    | | cache/{TICKER}_| | logs/agent_trace.jsonl      |
| agentic_report.md    | | YYYY-MM-DD.json| |                             |
+----------------------+ +--------+-------+ +-----------------------------+
                                  |
                                  v
                  +-----------------------------+
                  | Later run with use_cache    |
                  +--------------+--------------+
                                 |
                                 v
                  +-----------------------------+
                  | Return cached payload       |
                  | cache_hit=True              |
                  +-----------------------------+
```

The cache is intentionally simple local JSON. It demonstrates stateful behavior without requiring Redis, a database, or cloud storage.

## 7. Optional Cloud Deployment Shape

```text
+---------------------------+
| User / Notebook / Cron    |
+-------------+-------------+
              |
              v
+---------------------------+
| API or Worker Service     |
| FastAPI, job runner, VM   |
+-------------+-------------+
              |
              v
+-------------------------------------------------------------+
| Containerized Python Runtime                                |
|                                                             |
|  +-------------------+  +-------------------+  +----------+ |
|  | Task 1 jobs       |  | Task 2 jobs       |  | Task 3   | |
|  | research reports  |  | train/inference   |  | agents   | |
|  +---------+---------+  +---------+---------+  +-----+----+ |
|            |                      |                  |      |
+------------+----------------------+------------------+------+
             |                      |                  |
             v                      v                  v
 +---------------------+  +-------------------+  +---------------------+
 | Object Storage      |  | Secrets Manager   |  | Managed Logs/Cache  |
 | reports/models      |  | provider tokens   |  | traces + memory     |
 +----------+----------+  +---------+---------+  +----------+----------+
            |                       |                       |
            +-----------------------+-----------------------+
                                    |
                                    v
              +--------------------------------------------+
              | External Services                          |
              | yfinance, DuckDuckGo, Groq/OpenRouter, HF  |
              +--------------------------------------------+
```

## 8. Artifact and Review Flow

```text
+------------------------------+
| Execute notebooks and scripts|
+--------------+---------------+
               |
               v
+------------------------------+
| Generate artifacts           |
+--------------+---------------+
               |
     +---------+----------+----------------+
     |                    |                |
     v                    v                v
+------------+   +----------------+   +----------------+
| Task 1     |   | Task 2         |   | Task 3         |
| md/html/png|   | model + metrics|   | report/cache/  |
| warnings   |   | optional HF URL|   | JSONL traces   |
+-----+------+   +--------+-------+   +--------+-------+
      |                   |                    |
      +-------------------+--------------------+
                          |
                          v
             +------------------------------+
             | Validate                     |
             | pytest + manual review       |
             +--------------+---------------+
                            |
                            v
             +------------------------------+
             | Final submission             |
             | README, docs, citations,     |
             | reflection, outputs          |
             +------------------------------+
```
