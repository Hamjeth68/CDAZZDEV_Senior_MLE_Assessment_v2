"""Shared label definitions for the Task 2 sentiment classifier."""

LABELS = ["negative", "neutral", "positive"]
LABEL2ID = {label: index for index, label in enumerate(LABELS)}
ID2LABEL = {index: label for label, index in LABEL2ID.items()}
