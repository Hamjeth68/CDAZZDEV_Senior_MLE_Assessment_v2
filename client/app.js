const { useEffect, useMemo, useState } = React;

const PERIODS = ["6mo", "1y", "2y", "5y"];
const SAMPLE_TICKERS = ["MSFT", "AAPL", "GOOGL", "NVDA", "TSLA"];
const RECENT_TICKERS_KEY = "era_recent_tickers";
const KPI_STORAGE_KEY = "era_dashboard_kpis";

function App() {
  const [status, setStatus] = useState(null);
  const [task, setTask] = useState("task1");
  const [ticker, setTicker] = useState("MSFT");
  const [period, setPeriod] = useState("2y");
  const [headlineCount, setHeadlineCount] = useState(10);
  const [useCache, setUseCache] = useState(true);
  const [sentimentText, setSentimentText] = useState("Microsoft shares rose after cloud revenue beat analyst expectations.");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recentTickers, setRecentTickers] = useState([]);
  const [runCount, setRunCount] = useState(0);
  const [lastRunTime, setLastRunTime] = useState("");
  const [lastTask, setLastTask] = useState("");

  useEffect(() => {
    apiGet("/api/status").then(setStatus).catch((err) => setError(err.message));

    try {
      const stored = JSON.parse(localStorage.getItem(RECENT_TICKERS_KEY) || "[]");
      if (Array.isArray(stored)) {
        setRecentTickers(stored.slice(0, 5));
      }
    } catch {
      // ignore parse failures
    }

    try {
      const kpis = JSON.parse(localStorage.getItem(KPI_STORAGE_KEY) || "{}");
      if (kpis) {
        setRunCount(kpis.runCount || 0);
        setLastRunTime(kpis.lastRunTime || "");
        setLastTask(kpis.lastTask || "");
      }
    } catch {
      // ignore parse failures
    }
  }, []);

  const canRun = useMemo(() => {
    if (task === "task2") return sentimentText.trim().length > 0;
    return ticker.trim().length > 0;
  }, [task, ticker, sentimentText]);

  async function runWorkflow(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const endpoint = task === "task1" ? "/api/task1/research" : task === "task3" ? "/api/task3/agentic" : "/api/task2/sentiment";
      const body = task === "task2"
        ? { text: sentimentText }
        : {
            ticker,
            period,
            min_headlines: Number(headlineCount),
            news_count: Number(headlineCount),
            use_cache: useCache,
          };
      const response = await apiPost(endpoint, body);
      setResult(response);
      if (task !== "task2") {
        saveRecentTicker(ticker, setRecentTickers);
      }
      const nextRunCount = runCount + 1;
      const nextLastRunTime = formatDateTime(new Date());
      const nextLastTask = task === "task1" ? "Equity Analyst" : task === "task3" ? "Agent Research" : "Sentiment Classifier";
      setRunCount(nextRunCount);
      setLastRunTime(nextLastRunTime);
      setLastTask(nextLastTask);
      localStorage.setItem(KPI_STORAGE_KEY, JSON.stringify({ runCount: nextRunCount, lastRunTime: nextLastRunTime, lastTask: nextLastTask }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <div>
          <p className="eyebrow">Portfolio project</p>
          <h1>Equity Research Assistant</h1>
          <p className="subhead">Interactive market research, sentiment inference, and agentic analysis in one deployable dashboard.</p>
        </div>
        <ConfigPills status={status} />
      </header>

      <section className="hero-grid">
        <article className="hero-card">
          <p className="eyebrow">What this project shows</p>
          <h2>Python workflows, ML, and product design</h2>
          <p>Designed for your CV, this project demonstrates a full-stack portfolio approach: data ingestion, model inference, LLM validation, and a polished UI.</p>
        </article>
        <article className="hero-card">
          <p className="eyebrow">Why it matters</p>
          <h2>Market research turned into stories</h2>
          <p>It combines technical indicators, news sentiment, and agentic analysis so users can review signal-based recommendations and generated research narratives.</p>
        </article>
        <article className="hero-card">
          <p className="eyebrow">Go-to-market angle</p>
          <h2>A demo-ready fintech prototype</h2>
          <p>This app is built to show investors and recruiters an AI-powered financial advisory workflow, with clear metrics, outputs, and a user-friendly dashboard.</p>
        </article>
      </section>

      <KpiSummary runCount={runCount} lastRunTime={lastRunTime} lastTask={lastTask} />
      <FeatureCards />

      <section className="workspace">
        <form className="control-panel" onSubmit={runWorkflow}>
          <div className="panel-title">
            <span className="pulse-dot" />
            <div>
              <strong>Mission Control</strong>
              <p>{task === "task1" ? "Single-ticker research brief" : task === "task3" ? "Two-agent market synthesis" : "Fine-tuned sentiment inference"}</p>
            </div>
          </div>
          <SegmentedControl value={task} onChange={setTask} />
          <SampleTickerRow onSelect={(value) => { setTicker(value); setTask("task1"); }} samples={SAMPLE_TICKERS} />
          <RecentTickerRow tickers={recentTickers} onSelect={(value) => { setTicker(value); setTask("task1"); }} />

          {task === "task2" ? (
            <label className="field">
              <span>Headline or market text</span>
              <textarea value={sentimentText} onChange={(event) => setSentimentText(event.target.value)} rows="8" />
            </label>
          ) : (
            <>
              <label className="field">
                <span>Ticker</span>
                <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} placeholder="MSFT" />
              </label>
              <div className="grid-two">
                <label className="field">
                  <span>Period</span>
                  <select value={period} onChange={(event) => setPeriod(event.target.value)}>
                    {PERIODS.map((item) => <option key={item}>{item}</option>)}
                  </select>
                </label>
                <label className="field">
                  <span>{task === "task1" ? "Headlines" : "News count"}</span>
                  <input type="number" min="0" max="25" value={headlineCount} onChange={(event) => setHeadlineCount(event.target.value)} />
                </label>
              </div>
              {task === "task3" && (
                <label className="check-row">
                  <input type="checkbox" checked={useCache} onChange={(event) => setUseCache(event.target.checked)} />
                  <span>Use cached agent report when available</span>
                </label>
              )}
            </>
          )}

          <button className="run-button" disabled={!canRun || loading}>
            {loading ? "Running analysis..." : "Run analysis"}
          </button>
          <AgentFlow task={task} loading={loading} />
          {error && <div className="error">{error}</div>}
        </form>

        <ResultsPanel task={task} result={result} loading={loading} />
      </section>
    </main>
  );
}

function saveRecentTicker(ticker, setRecentTickers) {
  const normalized = ticker?.trim().toUpperCase();
  if (!normalized) return;
  const current = JSON.parse(localStorage.getItem(RECENT_TICKERS_KEY) || "[]");
  const next = [normalized, ...current].filter((item, index, all) => item && all.indexOf(item) === index).slice(0, 5);
  localStorage.setItem(RECENT_TICKERS_KEY, JSON.stringify(next));
  setRecentTickers(next);
  return next;
}

function SampleTickerRow({ samples, onSelect }) {
  return (
    <div className="sample-row">
      <span>Sample tickers:</span>
      {samples.map((symbol) => (
        <button key={symbol} type="button" onClick={() => onSelect(symbol)}>{symbol}</button>
      ))}
    </div>
  );
}

function RecentTickerRow({ tickers, onSelect }) {
  if (!tickers?.length) return null;
  return (
    <div className="recent-row">
      <span>Recent tickers:</span>
      {tickers.map((symbol) => (
        <button key={symbol} type="button" onClick={() => onSelect(symbol)}>{symbol}</button>
      ))}
    </div>
  );
}

function KpiSummary({ runCount, lastRunTime, lastTask }) {
  return (
    <section className="kpi-summary">
      <div>
        <p className="eyebrow">Usage KPIs</p>
        <h2>Dashboard performance at a glance</h2>
      </div>
      <div className="kpi-grid">
        <div className="kpi-card">
          <span>Analysis runs</span>
          <strong>{runCount}</strong>
        </div>
        <div className="kpi-card">
          <span>Last run</span>
          <strong>{lastRunTime || "Never"}</strong>
        </div>
        <div className="kpi-card">
          <span>Last workflow</span>
          <strong>{lastTask || "None"}</strong>
        </div>
      </div>
    </section>
  );
}

function ConfigPills({ status }) {
  const groq = status?.config?.groq_configured;
  const openrouter = status?.config?.openrouter_configured;
  const model = status?.task2_model_available;
  return (
    <div className="pills">
      <span className={groq ? "pill ok" : "pill"}>Groq {groq ? "linked" : "offline"}</span>
      <span className={openrouter ? "pill ok" : "pill"}>OpenRouter {openrouter ? "linked" : "offline"}</span>
      <span className={model ? "pill ok" : "pill"}>HF model {model ? "loaded" : "missing"}</span>
    </div>
  );
}

function SegmentedControl({ value, onChange }) {
  const options = [
    ["task1", "Equity Analyst"],
    ["task3", "Agent Research"],
    ["task2", "Sentiment Classifier"],
  ];
  return (
    <div className="segments" role="tablist">
      {options.map(([id, label]) => (
        <button key={id} type="button" className={value === id ? "active" : ""} onClick={() => onChange(id)}>
          {label}
        </button>
      ))}
    </div>
  );
}

function FeatureCards() {
  const cards = [
    {
      title: "Actionable equity insight",
      description: "Turn live ticker data and news into clear buy/hold/sell guidance backed by technical indicators and sentiment analysis.",
    },
    {
      title: "Transparent AI inference",
      description: "See the outputs, warnings, and raw JSON from the pipeline so every recommendation is verifiable and explainable.",
    },
    {
      title: "Agentic market research",
      description: "Combine a quant agent and a research agent to generate a narrative report that blends data signals with qualitative reasoning.",
    },
    {
      title: "Portfolio-ready storytelling",
      description: "Use the dashboard as a hiring artifact by showing a product prototype, a deployment plan, and a data-driven UX.",
    },
  ];
  return (
    <section className="feature-grid">
      {cards.map((card) => (
        <article key={card.title} className="feature-card">
          <h3>{card.title}</h3>
          <p>{card.description}</p>
        </article>
      ))}
    </section>
  );
}

function AgentFlow({ task, loading }) {
  const steps = task === "task1"
    ? ["Market data", "Indicators", "News sentiment", "Recommendation"]
    : task === "task3"
      ? ["Quant agent", "Research agent", "Memory", "Final report"]
      : ["Tokenizer", "Local model", "Label", "Confidence"];
  return (
    <div className="agent-flow">
      {steps.map((step, index) => (
        <div className={loading ? "flow-step active" : "flow-step"} key={step}>
          <span>{index + 1}</span>
          <p>{step}</p>
        </div>
      ))}
    </div>
  );
}

function ResultsPanel({ task, result, loading }) {
  if (loading) {
    return (
      <section className="result-panel empty ai-empty">
        <div className="scanner">
          <div className="scan-line" />
          <div className="node n1" />
          <div className="node n2" />
          <div className="node n3" />
        </div>
        <p>Analyzing live data, tools, and model outputs...</p>
      </section>
    );
  }
  if (!result) {
    return (
      <section className="result-panel empty ai-empty">
        <div className="scanner idle">
          <div className="scan-line" />
          <div className="node n1" />
          <div className="node n2" />
          <div className="node n3" />
        </div>
        <p>Select a workflow and launch analysis. Results will appear as an AI-readable research packet.</p>
      </section>
    );
  }
  if (result.error) {
    return <section className="result-panel"><h2>Run failed</h2><pre>{JSON.stringify(result, null, 2)}</pre></section>;
  }
  if (task === "task1") return <Task1Result result={result} />;
  if (task === "task3") return <Task3Result result={result} />;
  return <Task2Result result={result} />;
}

function Task1Result({ result }) {
  const summary = result.equity_summary || {};
  const snapshot = summary.indicator_snapshot || {};
  const rec = result.recommendation || {};
  const sentiment = result.sentiment || {};
  const chart = result.outputs?.chart;
  return (
    <section className="result-panel">
      <div className="result-header">
        <div>
          <p className="eyebrow">Analyst AI output</p>
          <h2>{result.ticker} {rec.recommendation || "Research"} Brief</h2>
          <p className="caption">{summary.company_name || "Company metadata unavailable"}</p>
        </div>
        <span className={`signal ${String(rec.recommendation || "Hold").toLowerCase()}`}>{rec.recommendation || "Hold"}</span>
      </div>
      {chart && <img className="chart" src={`/api/artifact?path=${encodeURIComponent(chart)}`} alt={`${result.ticker} price chart`} />}
      <div className="metrics">
        <Metric label="Current price" value={money(summary.current_price)} />
        <Metric label="Market cap" value={largeMoney(summary.market_cap)} />
        <Metric label="RSI 14" value={number(snapshot.rsi_14)} />
        <Metric label="Sentiment" value={sentiment.aggregate_label || "Unavailable"} />
      </div>
      <section className="narrative">
        <h3>Rationale</h3>
        <p>{rec.rationale || "No rationale returned."}</p>
      </section>
      <Warnings warnings={result.warnings} />
      <Headlines headlines={result.headlines} />
      <ArtifactLinks outputs={result.outputs} />
      <ResultActions result={result} task="task1" />
      <RawJson result={result} />
    </section>
  );
}

function Task3Result({ result }) {
  const quant = result.quant_brief || {};
  const research = result.research_brief || {};
  return (
    <section className="result-panel">
      <div className="result-header">
        <div>
          <p className="eyebrow">{result.cache_hit ? "Memory retrieval" : "Live agent run"}</p>
          <h2>{result.ticker} Agentic Report</h2>
          <p className="caption">Quant agent plus research agent synthesis</p>
        </div>
      </div>
      <div className="metrics">
        <Metric label="Latest close" value={money(quant.price_result?.data?.latest_close)} />
        <Metric label="Volatility" value={percent(quant.volatility_result?.data?.annualized_volatility)} />
        <Metric label="Headlines found" value={research.news_result?.data?.found ?? "0"} />
        <Metric label="Sentiment" value={research.sentiment_result?.data?.aggregate_label || "Unavailable"} />
      </div>
      <article className="markdown-report">{result.final_report}</article>
      <Warnings warnings={result.warnings} />
      <ArtifactLinks outputs={{ markdown: result.output_path }} />
      <ResultActions result={result} task="task3" />
      <RawJson result={result} />
    </section>
  );
}

function Task2Result({ result }) {
  return (
    <section className="result-panel">
      <div className="result-header">
        <div>
          <p className="eyebrow">Local fine-tuned model</p>
          <h2>Sentiment Prediction</h2>
          <p className="caption">Transformer classification output</p>
        </div>
        <span className="signal hold">{result.prediction?.label || "LABEL"}</span>
      </div>
      <div className="metrics">
        <Metric label="Score" value={percent(result.prediction?.score)} />
        <Metric label="Model" value="Local Task 2" />
      </div>
      <section className="narrative">
        <h3>Input</h3>
        <p>{result.text}</p>
      </section>
      <ResultActions result={result} task="task2" />
      <RawJson result={result} />
    </section>
  );
}

function Metric({ label, value }) {
  return <div className="metric"><span>{label}</span><strong>{value ?? "Unavailable"}</strong></div>;
}

function ResultActions({ result, task }) {
  if (!result) return null;
  return (
    <section className="result-actions">
      <button type="button" className="secondary-button" onClick={() => downloadJson(result)}>Download JSON</button>
      <button type="button" className="secondary-button" onClick={() => downloadReport(result, task)}>Download summary</button>
      <button type="button" className="secondary-button" onClick={() => copySummary(result, task)}>Copy summary</button>
      <button type="button" className="secondary-button" onClick={() => downloadPdf(result, task)}>Download PDF</button>
    </section>
  );
}

function downloadJson(result) {
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  triggerFileDownload(blob, "equity-research-result.json");
}

function downloadReport(result, task) {
  const text = getResultSummary(result, task);
  const blob = new Blob([text], { type: "text/plain" });
  triggerFileDownload(blob, "equity-research-summary.txt");
}

function copySummary(result, task) {
  const text = getResultSummary(result, task);
  navigator.clipboard.writeText(text).catch(() => {});
}

function triggerFileDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function downloadPdf(result, task) {
  const pdf = new window.jspdf.jsPDF();
  const text = getResultSummary(result, task);
  const lines = pdf.splitTextToSize(text, 180);
  pdf.setFontSize(12);
  pdf.text(lines, 15, 20);
  pdf.save("equity-research-report.pdf");
}

function formatDateTime(date) {
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getResultSummary(result, task) {
  if (task === "task1") {
    const ticker = result.ticker || "Unknown ticker";
    const recommendation = result.recommendation?.recommendation || "No recommendation";
    const rationale = result.recommendation?.rationale || "No rationale provided.";
    const sentiment = result.sentiment?.aggregate_label || "Unavailable";
    return `Ticker: ${ticker}\nRecommendation: ${recommendation}\nSentiment: ${sentiment}\nRationale: ${rationale}`;
  }
  if (task === "task3") {
    return result.final_report || JSON.stringify(result, null, 2);
  }
  if (task === "task2") {
    const label = result.prediction?.label || "Unknown";
    const score = result.prediction?.score != null ? `${(result.prediction.score * 100).toFixed(1)}%` : "Unavailable";
    return `Text: ${result.text}\nPrediction: ${label}\nConfidence: ${score}`;
  }
  return JSON.stringify(result, null, 2);
}

function Warnings({ warnings }) {
  if (!warnings?.length) return null;
  return <section className="warnings"><h3>Warnings</h3>{warnings.map((item, index) => <p key={index}>{item}</p>)}</section>;
}

function Headlines({ headlines }) {
  if (!headlines?.length) return null;
  return (
    <section className="narrative">
      <h3>Headlines</h3>
      <ul>{headlines.slice(0, 6).map((item, index) => <li key={index}>{item.title}</li>)}</ul>
    </section>
  );
}

function ArtifactLinks({ outputs }) {
  const entries = Object.entries(outputs || {}).filter(([, value]) => value);
  if (!entries.length) return null;
  return (
    <section className="artifact-row">
      {entries.map(([label, path]) => <a key={label} href={`/api/artifact?path=${encodeURIComponent(path)}`} target="_blank" rel="noreferrer">{label}</a>)}
    </section>
  );
}

function RawJson({ result }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="raw">
      <button type="button" onClick={() => setOpen(!open)}>{open ? "Hide" : "Show"} raw JSON</button>
      {open && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </section>
  );
}

async function apiGet(url) {
  const response = await fetch(url);
  return readResponse(response);
}

async function apiPost(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readResponse(response);
}

async function readResponse(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function money(value) {
  return typeof value === "number" ? `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "Unavailable";
}

function largeMoney(value) {
  if (typeof value !== "number") return "Unavailable";
  const units = ["", "K", "M", "B", "T"];
  let index = 0;
  let scaled = value;
  while (Math.abs(scaled) >= 1000 && index < units.length - 1) {
    scaled /= 1000;
    index += 1;
  }
  return `$${scaled.toLocaleString(undefined, { maximumFractionDigits: 2 })}${units[index]}`;
}

function number(value) {
  return typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "Unavailable";
}

function percent(value) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "Unavailable";
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
