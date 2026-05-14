import csv
from pathlib import Path

from task2_finetuning.src.labels import LABEL2ID, LABELS


def test_task2_dataset_has_expected_labels():
    data_path = Path("task2_finetuning/data/financial_headlines_sample.csv")
    rows = list(csv.DictReader(data_path.open(encoding="utf-8")))

    assert rows
    assert {row["label"] for row in rows} == set(LABELS)
    assert all(row["text"].strip() for row in rows)


def test_task2_labels_are_stable_for_huggingface_model_config():
    assert LABELS == ["negative", "neutral", "positive"]
    assert LABEL2ID == {"negative": 0, "neutral": 1, "positive": 2}
