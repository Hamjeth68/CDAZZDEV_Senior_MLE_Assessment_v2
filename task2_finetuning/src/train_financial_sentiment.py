"""Fine-tune a Hugging Face text classifier on financial headlines.

The default configuration is intentionally small so it can run on CPU for an
assessment demo. For a stronger model, add more labeled data and train longer.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from task2_finetuning.src.labels import ID2LABEL, LABEL2ID


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT / "data" / "financial_headlines_sample.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "financial-sentiment-model"
DEFAULT_CACHE_DIR = ROOT / "outputs" / "hf_cache"


def _require_hf_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Task 2 dependencies are missing. Install them with:\n"
            "  pip install -r task2_finetuning/requirements-task2.txt"
        ) from exc
    return torch, AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments


class HeadlineDataset:
    def __init__(self, rows: pd.DataFrame, tokenizer: Any, max_length: int, torch_module: Any):
        self.rows = rows.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.torch = torch_module

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        row = self.rows.iloc[index]
        encoded = self.tokenizer(
            str(row["text"]),
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = self.torch.tensor(int(row["labels"]), dtype=self.torch.long)
        return item


def _load_and_split_data(data_path: Path, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_csv(data_path)
    required_columns = {"text", "label"}
    if not required_columns.issubset(frame.columns):
        raise ValueError(f"Dataset must contain columns: {sorted(required_columns)}")

    frame = frame.dropna(subset=["text", "label"]).copy()
    frame["label"] = frame["label"].astype(str).str.strip().str.lower()
    unknown_labels = sorted(set(frame["label"]) - set(LABEL2ID))
    if unknown_labels:
        raise ValueError(f"Unexpected labels in dataset: {unknown_labels}")
    frame["labels"] = frame["label"].map(LABEL2ID).astype(int)

    test_rows = []
    train_rows = []
    for _, group in frame.groupby("labels"):
        shuffled = group.sample(frac=1.0, random_state=seed)
        test_count = max(1, int(round(len(shuffled) * 0.25)))
        test_rows.append(shuffled.iloc[:test_count])
        train_rows.append(shuffled.iloc[test_count:])

    train = pd.concat(train_rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    test = pd.concat(test_rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return train, test


def _macro_f1(predictions: np.ndarray, labels: np.ndarray) -> float:
    scores: list[float] = []
    for label_id in sorted(ID2LABEL):
        true_positive = int(((predictions == label_id) & (labels == label_id)).sum())
        false_positive = int(((predictions == label_id) & (labels != label_id)).sum())
        false_negative = int(((predictions != label_id) & (labels == label_id)).sum())

        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores.append(f1)
    return float(np.mean(scores))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune a financial headline sentiment classifier.")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--model-name", default="distilbert-base-uncased")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--hub-model-id", default=None, help="Example: your-username/financial-sentiment-distilbert")
    parser.add_argument("--private", action="store_true", help="Create/update the Hub repo as private when pushing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    torch, AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments = _require_hf_dependencies()

    if args.push_to_hub and not args.hub_model_id:
        raise SystemExit("--hub-model-id is required when --push-to-hub is set.")

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, cache_dir=str(args.cache_dir / "transformers"))
    train_frame, eval_frame = _load_and_split_data(args.data_path, args.seed)
    train_dataset = HeadlineDataset(train_frame, tokenizer, args.max_length, torch)
    eval_dataset = HeadlineDataset(eval_frame, tokenizer, args.max_length, torch)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        cache_dir=str(args.cache_dir / "transformers"),
    )

    def compute_metrics(eval_prediction: Any) -> dict[str, float]:
        logits, labels = eval_prediction
        predictions = np.argmax(logits, axis=-1)
        accuracy = float((predictions == labels).mean())
        return {"accuracy": accuracy, "macro_f1": _macro_f1(predictions, labels)}

    training_kwargs: dict[str, Any] = {
        "output_dir": str(args.output_dir),
        "learning_rate": args.learning_rate,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "num_train_epochs": args.epochs,
        "weight_decay": 0.01,
        "logging_steps": 5,
        "save_strategy": "epoch",
        "report_to": "none",
        "seed": args.seed,
        "push_to_hub": args.push_to_hub,
    }

    signature = inspect.signature(TrainingArguments.__init__)
    if "eval_strategy" in signature.parameters:
        training_kwargs["eval_strategy"] = "epoch"
    else:
        training_kwargs["evaluation_strategy"] = "epoch"

    if args.push_to_hub:
        training_kwargs["hub_model_id"] = args.hub_model_id
        training_kwargs["hub_private_repo"] = args.private
        if os.getenv("HF_TOKEN"):
            training_kwargs["hub_token"] = os.getenv("HF_TOKEN")

    trainer_kwargs: dict[str, Any] = {
        "model": model,
        "args": TrainingArguments(**training_kwargs),
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset,
        "compute_metrics": compute_metrics,
    }
    trainer_signature = inspect.signature(Trainer.__init__)
    if "tokenizer" in trainer_signature.parameters:
        trainer_kwargs["tokenizer"] = tokenizer
    elif "processing_class" in trainer_signature.parameters:
        trainer_kwargs["processing_class"] = tokenizer

    trainer = Trainer(**trainer_kwargs)

    trainer.train()
    metrics = trainer.evaluate()
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))

    metrics_path = args.output_dir / "eval_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    if args.push_to_hub:
        trainer.push_to_hub(
            commit_message="Add Task 2 fine-tuned financial sentiment classifier",
            model_card_kwargs={
                "language": "en",
                "license": "mit",
                "tags": ["financial-sentiment", "text-classification", "assessment"],
            },
        )

    print(f"Saved model to: {args.output_dir}")
    print(f"Saved metrics to: {metrics_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
