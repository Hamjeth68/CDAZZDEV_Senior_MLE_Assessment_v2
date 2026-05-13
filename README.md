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
<<<<<<< ours
   - Set `GROQ_API_KEY` and/or `OPENROUTER_API_KEY`
=======
   - Set at least one provider key: `GROQ_API_KEY` **or** `OPENROUTER_API_KEY`


## Provider requirement for assessment
GROQ is **not mandatory** unless your assessor explicitly requires a specific provider.
This project supports either provider, so one valid key is sufficient:
- `GROQ_API_KEY`
- `OPENROUTER_API_KEY`

## API keys (where to get them)
- **Groq**: sign in at `https://console.groq.com`, then create a key at `https://console.groq.com/keys`.
- **OpenRouter**: sign in at `https://openrouter.ai`, then create a key at `https://openrouter.ai/keys`.

Set either or both in your local `.env` file (never commit populated keys).

## Troubleshooting API signup errors
If Groq shows **"<email> does not belong to any organizations"** during signup:
- You likely used a workspace/SSO flow that expects an invited organization account.
- Go back and create/use a **personal account** first, or use a different email that is not tied to an enterprise SSO tenant.
- If your company manages Groq access, ask your admin to invite your email to the org before retrying.

If you are blocked on Groq, continue with **OpenRouter** only (the project supports either provider).
>>>>>>> theirs

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
