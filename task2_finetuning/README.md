# Task 2: Hugging Face Fine-Tuning

## Objective
Task 2 fine-tunes a small Hugging Face transformer for financial headline sentiment classification. The model predicts one of three labels:

- `positive`
- `neutral`
- `negative`

This is intentionally lightweight so it can run on a normal laptop/CPU for an assessment demo. The included CSV is a small reproducible sample; for a production model, replace it with a larger labeled financial-news dataset.

## Files
- `data/financial_headlines_sample.csv` - small labeled training/evaluation sample.
- `src/train_financial_sentiment.py` - trains, evaluates, saves, and optionally uploads the model.
- `src/predict_sentiment.py` - runs local inference after training.
- `requirements-task2.txt` - optional Hugging Face dependencies for Task 2 only.

## Install Task 2 Dependencies
From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r task2_finetuning\requirements-task2.txt
```

## Train Locally
From the repository root:

```powershell
python -m task2_finetuning.src.train_financial_sentiment --epochs 1
```

Expected local outputs:

- `task2_finetuning/outputs/financial-sentiment-model/`
- `task2_finetuning/outputs/financial-sentiment-model/eval_metrics.json`

## Test Local Inference
After training:

```powershell
python -m task2_finetuning.src.predict_sentiment --text "Shares fell after the company cut its revenue forecast."
```

## Upload to Hugging Face Hub
Create a Hugging Face account first, then create a **write** token at:

```text
https://huggingface.co/settings/tokens
```

In PowerShell, log in without committing the token:

```powershell
hf auth login
```

Paste your token when prompted.

If your installed Hugging Face CLI exposes the older command name instead, use:

```powershell
huggingface-cli login
```

Then train and push:

```powershell
python -m task2_finetuning.src.train_financial_sentiment --epochs 1 --push-to-hub --hub-model-id YOUR_USERNAME/financial-sentiment-distilbert