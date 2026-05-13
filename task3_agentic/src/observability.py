from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from task3_agentic.src.schemas import AgentTraceRecord, ToolStatus

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "agent_trace.jsonl"
DEFAULT_SESSION_ID = uuid4().hex


def truncate_output(output: Any, max_chars: int = 200) -> str:
    try:
        if hasattr(output, "model_dump"):
            text = json.dumps(output.model_dump(mode="json"), default=str, sort_keys=True)
        else:
            text = json.dumps(output, default=str, sort_keys=True)
    except TypeError:
        text = str(output)
    return text[:max_chars]


def log_tool_call(
    tool_name: str,
    inputs: dict[str, Any],
    output: Any,
    duration_ms: int,
    status: ToolStatus,
    agent: str = "task3_agentic",
    session_id: str | None = None,
) -> AgentTraceRecord:
    record = AgentTraceRecord(
        timestamp=datetime.utcnow(),
        session_id=session_id or DEFAULT_SESSION_ID,
        agent=agent,
        tool_name=tool_name,
        inputs=inputs,
        output_preview=truncate_output(output),
        duration_ms=max(0, int(duration_ms)),
        status=status,
    )
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.model_dump(mode="json"), default=str) + "\n")
    return record
