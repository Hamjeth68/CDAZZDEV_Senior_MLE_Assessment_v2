"""LangGraph orchestration for the Task 3 multi-agent workflow."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError as exc:  # pragma: no cover - dependency availability is environment-specific.
    raise ImportError(
        "LangGraph is required for Task 3. Install dependencies with `pip install -r requirements.txt`."
    ) from exc

from shared.schemas import AgentDataBrief, AgentToolTrace, FinalResearchReport
from task3_agentic.src.agents import (
    ClarificationAnswer,
    answer_clarification,
    ask_data_clarification,
    render_report,
    run_data_analyst,
    run_research_writer,
)


class AgentState(TypedDict, total=False):
    """Explicit shared state passed between LangGraph nodes."""

    ticker: str
    session_id: str
    data_brief: AgentDataBrief
    clarification_question: str
    clarification_answer: ClarificationAnswer
    final_report: FinalResearchReport
    rendered_report: str
    trace: list[dict[str, Any]]
    news: list[Any]
    search_results: list[dict[str, str]]


def _event(node: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "node": node,
        "message": message,
        "payload": payload or {},
    }


def _trace_models(models: list[AgentToolTrace]) -> list[dict[str, Any]]:
    return [model.model_dump(mode="json") for model in models]


def _append_trace(state: AgentState, *events: dict[str, Any]) -> list[dict[str, Any]]:
    return [*(state.get("trace") or []), *events]


def agent_a_data_node(state: AgentState) -> AgentState:
    data_brief = run_data_analyst(state["ticker"], state["session_id"])
    return {
        **state,
        "data_brief": data_brief,
        "trace": _append_trace(
            state,
            _event("agent_a_data_analyst", "Agent A produced AgentDataBrief.", data_brief.model_dump(mode="json")),
            *_trace_models(data_brief.tool_traces),
        ),
    }


def agent_b_question_node(state: AgentState) -> AgentState:
    question = ask_data_clarification(state["data_brief"])
    return {
        **state,
        "clarification_question": question,
        "trace": _append_trace(
            state,
            _event("agent_b_critique", "Agent B asked one specific clarification.", {"question": question}),
        ),
    }


def agent_a_answer_node(state: AgentState) -> AgentState:
    answer = answer_clarification(state["clarification_question"], state["data_brief"])
    return {
        **state,
        "clarification_answer": answer,
        "trace": _append_trace(
            state,
            _event("agent_a_clarification", "Agent A returned structured clarification data.", answer.model_dump(mode="json")),
        ),
    }


def agent_b_report_node(state: AgentState) -> AgentState:
    report, tool_traces, metadata = run_research_writer(
        state["data_brief"],
        state["session_id"],
        state["clarification_answer"],
    )
    rendered = render_report(report)
    return {
        **state,
        "final_report": report,
        "rendered_report": rendered,
        "news": metadata["news"],
        "search_results": metadata["search_results"],
        "trace": _append_trace(
            state,
            _event("agent_b_research_writer", "Agent B produced final report.", report.model_dump(mode="json")),
            *_trace_models(tool_traces),
            _event("workflow_complete", "LangGraph workflow completed without manual intervention."),
        ),
    }


def build_research_graph():
    """Build and compile the required LangGraph state machine."""

    graph = StateGraph(AgentState)
    graph.add_node("agent_a_data_analyst", agent_a_data_node)
    graph.add_node("agent_b_critique", agent_b_question_node)
    graph.add_node("agent_a_clarification", agent_a_answer_node)
    graph.add_node("agent_b_research_writer", agent_b_report_node)

    graph.set_entry_point("agent_a_data_analyst")
    graph.add_edge("agent_a_data_analyst", "agent_b_critique")
    graph.add_edge("agent_b_critique", "agent_a_clarification")
    graph.add_edge("agent_a_clarification", "agent_b_research_writer")
    graph.add_edge("agent_b_research_writer", END)
    return graph.compile()


def print_full_trace(state: AgentState) -> None:
    """Print the full workflow trace for notebook output."""

    print("FULL LANGGRAPH TRACE")
    print(json.dumps(state.get("trace", []), indent=2, default=str))


def run_research_workflow(ticker: str, print_trace: bool = True) -> AgentState:
    """Run the multi-agent workflow to completion and optionally print the full trace."""

    initial_state: AgentState = {
        "ticker": ticker.strip().upper(),
        "session_id": str(uuid.uuid4()),
        "trace": [_event("workflow_start", "LangGraph workflow started.", {"ticker": ticker.strip().upper()})],
    }
    app = build_research_graph()
    final_state = app.invoke(initial_state)
    if print_trace:
        print_full_trace(final_state)
        print("\nFINAL REPORT")
        print(final_state["rendered_report"])
    return final_state


__all__ = [
    "AgentState",
    "build_research_graph",
    "print_full_trace",
    "run_research_workflow",
]

