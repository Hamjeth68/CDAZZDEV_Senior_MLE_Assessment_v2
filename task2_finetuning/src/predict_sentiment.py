"""Run inference with the local Task 2 fine-tuned model."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
import os


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "outputs" / "financial-sentiment-model"
DEFAULT_CACHE_DIR = ROOT / "outputs" / "hf_cache"


def _require_hf_dependencies() -> tuple[Any, Any, Any]:
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    except ImportError as exc:
        raise SystemExit(
            "Task 2 dependencies are missing. Install them with:\n"
            "  pip install -r task2_finetuning/requirements-task2.txt"
        ) from exc
    return AutoModelForSequenceClassification, AutoTokenizer, pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict financial sentiment with the fine-tuned model.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument(
        "--text",
        default="Microsoft shares rose after cloud revenue beat analyst expectations.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(args.cache_dir))
    AutoModelForSequenceClassification, AutoTokenizer, pipeline = _require_hf_dependencies()

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_dir)
    classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

    print(classifier(args.text)[0])


if __name__ == "__main__":
    main()
