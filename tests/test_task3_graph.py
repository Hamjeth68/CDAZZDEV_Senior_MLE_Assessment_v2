from types import SimpleNamespace

from task3_agentic.src import agents, graph
from task3_agentic.src.schemas import ToolResult


def _success(tool_name: str, data: dict) -> ToolResult:
    return ToolResult(status="success", tool_name=tool_name, data=data)


def test_run_two_agent_pipeline_returns_final_report(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(graph, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(graph, "load_cached_report", lambda *_: None)
    monkeypatch.setattr(graph, "save_cached_report", lambda *args, **kwargs: tmp_path / "cache.json")
    monkeypatch.setattr(
        agents,
        "get_price_data",
        lambda *_: _success("get_price_data", {"rows": 10, "latest_close": 420.0}),
    )
    monkeypatch.setattr(
        agents,
        "calculate_volatility",
        lambda *_: _success(
            "calculate_volatility",
            {"window": 30, "observations": 100, "annualized_volatility": 0.22},
        ),
    )
    monkeypatch.setattr(
        agents,
        "get_news",
        lambda *_: _success(
            "get_news",
            {"headlines": [{"title": "Microsoft expands AI cloud services"}]},
        ),
    )
    monkeypatch.setattr(
        agents,
        "llm_sentiment",
        lambda *_: _success(
            "llm_sentiment",
            {"headlines_analyzed": 1, "aggregate_label": "positive", "aggregate_score": 0.6},
        ),
    )
    monkeypatch.setattr(
        agents,
        "web_search",
        lambda *_: _success("web_search", {"snippets": [{"title": "Analyst outlook"}]}),
    )

    result = graph.run_two_agent_pipeline("msft", use_cache=False)

    assert result["ticker"] == "MSFT"
    assert "Agentic Financial Research Report: MSFT" in result["final_report"]
    assert (tmp_path / "MSFT_agentic_report.md").exists()
