# Equity Research Assistant — Portfolio Project

## Scope
This repository contains a polished portfolio project for equity research automation and AI-powered financial insights.
- **Task 1** - Interactive equity research and market signal briefing
- **Task 2** - Fine-tuned financial sentiment classification
- **Task 3** - Agentic research orchestration with memory and traceability

## Product positioning
The Equity Research Assistant is designed as a market-facing analytics prototype for investment analysts and fintech teams.
It combines structured pricing signals, news sentiment, and agentic report synthesis into an accessible dashboard.

### Selling points
- AI-assisted equity research that turns ticker data and headlines into actionable insights.
- Quick start sample tickers, recent query recall, and exportable research summaries for real demo readiness.
- A transparent pipeline with report outputs, charts, and raw JSON for validation.
- Provider-agnostic LLM integration plus local sentiment inference from a fine-tuned model.
- Suitable for portfolio presentation because it demonstrates backend engineering, ML, and frontend product design.

## Layout
- `shared/` - reusable config, schemas, prompts, errors, logging
- `task1_financial/` - Task 1 implementation, notebook, outputs
- `task2_finetuning/` - Task 2 Hugging Face fine-tuning workflow, sample data, model upload path
- `task3_agentic/` - Task 3 implementation, notebook, logs, cache, outputs
- `docs/ARCHITECTURE.md` - ASCII architecture diagrams for the repository, task flows, and deployment shape
- `CITATIONS.md` - AI usage and reference disclosure
- `REFLECTION.md` - design decisions, limitations, next improvements

## Setup (Python 3.11)
1. Create a virtual environment.
   - PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1`
   - CMD: `python -m venv .venv && .venv\Scripts\activate.bat`
2. Install base dependencies: `pip install -r requirements.txt`
3. Configure local environment:
   - Copy `.env.example` to `.env`
   - Set at least one provider key: `GROQ_API_KEY` **or** `OPENROUTER_API_KEY`

## Provider Requirement for Assessment
GROQ is **not mandatory** unless your assessor explicitly requires a specific provider.
This project supports either provider, so one valid key is sufficient:
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`

## API Keys
- **Groq**: sign in at `https://console.groq.com`, then create a key at `https://console.groq.com/keys`.
- **OpenRouter**: sign in at `https://openrouter.ai`, then create a key at `https://openrouter.ai/keys`.
- **Hugging Face**: sign in at `https://huggingface.co`, then create a write token at `https://huggingface.co/settings/tokens`.

Set provider keys only in your local `.env` file or terminal session. Never commit populated keys.

## Troubleshooting API Signup Errors
If Groq shows **"<email> does not belong to any organizations"** during signup:
- You likely used a workspace/SSO flow that expects an invited organization account.
- Go back and create/use a personal account first, or use a different email that is not tied to an enterprise SSO tenant.
- If your company manages Groq access, ask your admin to invite your email to the org before retrying.

If you are blocked on Groq, continue with **OpenRouter** only. The project supports either provider.

## Run
- Task 1: open and run `task1_financial/task1_equity_research.ipynb`
- Task 2: follow `task2_finetuning/README.md`
- Task 3: open and run `task3_agentic/task3_agentic_research.ipynb`

## React Client
You can run the local portfolio dashboard instead of printing outputs in the terminal:

```powershell
python app_server.py --port 8000
```

Then open `http://127.0.0.1:8000`.

The client exposes:
- Task 1 equity brief generation with chart/report artifact links.
- Task 3 agentic research reports with cache toggle and raw JSON.
- Task 2 local sentiment prediction using the fine-tuned classifier.

The UI is served from `client/` and uses CDN React/Babel, so no npm setup is required.

> Note: The full interactive backend requires a local Python runtime and provider credentials. For zero-cost public visibility, publish the client as a static portfolio landing page using GitHub Pages and run the backend locally for the full experience.

## Marketing landing page
A polished marketing landing page has been added at `client/landing.html`.
Use this page to showcase:
- the product value proposition,
- core customer benefits,
- the real-world use cases,
- and how to launch the interactive dashboard.

## Zero-cost deployment
### GitHub Pages
1. Publish the static files from `client/`.
2. Set `landing.html` as the marketing page and keep `index.html` as the interactive demo.
3. If you want the landing page to load at the root, rename `landing.html` to `index.html` on the published branch or copy its contents to the published root index.

#### GitHub Actions deployment
A ready-to-use GitHub Actions workflow is included in `.github/workflows/deploy-pages.yml`.
This workflow uploads the `client/` folder as a Pages artifact and deploys it automatically to `gh-pages`.

#### Local deployment script
A small local deployment helper is included at `deploy_github_pages.ps1` for users with the GitHub CLI.

### Docker deployment
Build and run the project locally in Docker:

```powershell
docker build -t equity-research-assistant .
docker run --rm -p 8000:8000 --env GROQ_API_KEY=your_key --env OPENROUTER_API_KEY=your_key equity-research-assistant
```

Or use Docker Compose:

```powershell
docker compose up --build
```

This container includes the Python backend, serves the client UI from the app server, and can run on any Docker host.

### Replit / Render
- Replit: create a Python Repl, upload this repository, and use `python app_server.py` as the run command.
- Render: create a free Web Service, select Python, and point it to this repository with `python app_server.py` as the start command.
- Configure `GROQ_API_KEY` or `OPENROUTER_API_KEY` in the environment settings for LLM workflows.

### Recommended GitHub Pages + local demo flow
- Host the static landing page publicly on GitHub Pages.
- Show the project as a portfolio item with a live marketing page.
- Mention in the landing page that the full interactive backend is available locally or via a free Python host.

Task 3 can also be run directly from PowerShell:

```powershell
python -c "from task3_agentic.src.graph import run_two_agent_pipeline; print(run_two_agent_pipeline('MSFT')['final_report'])"
```

## Task 2 Quick Start
Task 2 uses extra Hugging Face dependencies that are isolated from the base Task 1/Task 3 environment.

```powershell
pip install -r task2_finetuning\requirements-task2.txt
python -m task2_finetuning.src.train_financial_sentiment --epochs 1
```

To upload the trained model to Hugging Face Hub:

```powershell
hf auth login
python -m task2_finetuning.src.train_financial_sentiment --epochs 1 --push-to-hub --hub-model-id YOUR_USERNAME/financial-sentiment-distilbert
```

Replace `YOUR_USERNAME` with your Hugging Face username. The model link to submit will be:

```text
https://huggingface.co/YOUR_USERNAME/financial-sentiment-distilbert
```

## Submission Checks
- [ ] Task 1 notebook executed with outputs visible
- [ ] Task 2 model trained and Hugging Face model URL submitted
- [ ] Task 3 notebook executed with outputs visible
- [ ] No credentials committed
- [ ] `CITATIONS.md` complete
- [ ] `REFLECTION.md` <= 600 words
- [ ] `task3_agentic/logs/agent_trace.jsonl` generated

## Walkthrough Link
https://www.dropbox.com/scl/fo/t16kt9xp9fhab6z0rl5aw/AD40Apmfkl27CURrKQfUFaM?rlkey=6s48g1t4f39yk8asjynvof337&st=fvs4yun7&dl=0









