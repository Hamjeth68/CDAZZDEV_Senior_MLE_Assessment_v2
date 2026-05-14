"""Upload the saved Task 2 model directory to Hugging Face Hub."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "outputs" / "financial-sentiment-model"


def _require_hub_dependency() -> Any:
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise SystemExit(
            "huggingface_hub is missing. Install Task 2 dependencies with:\n"
            "  pip install -r task2_finetuning/requirements-task2.txt"
        ) from exc
    return HfApi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload the saved Task 2 model to Hugging Face Hub.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--hub-model-id", required=True, help="Example: your-username/financial-sentiment-distilbert")
    parser.add_argument("--private", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.model_dir.exists():
        raise SystemExit(f"Model directory does not exist: {args.model_dir}")

    HfApi = _require_hub_dependency()
    api = HfApi()
    api.create_repo(repo_id=args.hub_model_id, repo_type="model", private=args.private, exist_ok=True)
    api.upload_folder(
        repo_id=args.hub_model_id,
        repo_type="model",
        folder_path=str(args.model_dir),
        commit_message="Upload Task 2 fine-tuned financial sentiment classifier",
    )
    print(f"Uploaded model to: https://huggingface.co/{args.hub_model_id}")


if __name__ == "__main__":
    main()
