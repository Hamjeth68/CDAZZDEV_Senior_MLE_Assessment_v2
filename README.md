# CDAZZDEV Senior MLE Assessment (Task 1 + Task 3)

## Scope
This repository targets:
- **Task 1** — Financial AI equity research assistant
- **Task 3** — Agentic financial research with memory and observability

## Layout
- `shared/` — reusable config, schemas, prompts, errors, logging
- `task1_financial/` — Task 1 implementation, notebook, outputs
- `task3_agentic/` — Task 3 implementation, notebook, logs, cache, outputs
- `CITATIONS.md` — AI usage and reference disclosure
- `REFLECTION.md` — design decisions, limitations, next improvements

## Setup (Python 3.11)
1. Create a virtual environment.
   - PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1`
   - CMD: `python -m venv .venv && .venv\Scripts\activate.bat`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure local environment:
   - Copy `.env.example` to `.env`
   - Set `GROQ_API_KEY` and/or `OPENROUTER_API_KEY`

## Run
- Task 1: open and run `task1_financial/task1_equity_research.ipynb`
- Task 3: open and run `task3_agentic/task3_agentic_research.ipynb`

## Submission checks
- [ ] Notebooks executed with outputs visible
- [ ] No credentials committed
- [ ] `CITATIONS.md` complete
- [ ] `REFLECTION.md` <= 600 words
- [ ] `task3_agentic/logs/agent_trace.jsonl` generated

## Walkthrough link
Add your unlisted video URL before submission.
