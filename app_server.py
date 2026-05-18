"""Local web UI server for the Equity Research Assistant portfolio.

This dependency-light server exposes the existing Python workflows as JSON APIs
and serves the client dashboard from ``client/``.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from shared.config import get_safe_config_summary

ROOT = Path(__file__).resolve().parent
CLIENT_DIR = ROOT / "client"
TASK2_MODEL_DIR = ROOT / "task2_finetuning" / "outputs" / "financial-sentiment-model"
TASK2_CACHE_DIR = ROOT / "task2_finetuning" / "outputs" / "hf_cache"


class AppRequestHandler(BaseHTTPRequestHandler):
    server_version = "EquityResearchAssistant/1.0"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._send_json(
                {
                    "ok": True,
                    "config": get_safe_config_summary(),
                    "task2_model_available": TASK2_MODEL_DIR.exists(),
                }
            )
            return

        if parsed.path == "/api/artifact":
            self._serve_artifact(parse_qs(parsed.query).get("path", [""])[0])
            return

        self._serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/task1/research":
                self._send_json(self._task1(payload))
                return
            if parsed.path == "/api/task3/agentic":
                self._send_json(self._task3(payload))
                return
            if parsed.path == "/api/task2/sentiment":
                self._send_json(self._task2(payload))
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:  # Keep failures visible in the client.
            self._send_json(
                {"error": str(exc), "error_type": type(exc).__name__},
                status=HTTPStatus.BAD_REQUEST,
            )

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def _task1(self, payload: dict[str, Any]) -> dict[str, Any]:
        from task1_financial.src.pipeline import run_equity_research

        ticker = _required_string(payload, "ticker")
        period = str(payload.get("period") or "2y").strip()
        min_headlines = _bounded_int(payload.get("min_headlines"), default=10, minimum=0, maximum=25)
        render_reports = bool(payload.get("render_reports", True))
        return run_equity_research(
            ticker=ticker,
            period=period,
            min_headlines=min_headlines,
            render_reports=render_reports,
        )

    def _task3(self, payload: dict[str, Any]) -> dict[str, Any]:
        from task3_agentic.src.graph import run_two_agent_pipeline

        ticker = _required_string(payload, "ticker")
        period = str(payload.get("period") or "2y").strip()
        news_count = _bounded_int(payload.get("news_count"), default=8, minimum=0, maximum=20)
        use_cache = bool(payload.get("use_cache", True))
        return run_two_agent_pipeline(ticker=ticker, period=period, news_count=news_count, use_cache=use_cache)

    def _task2(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = _required_string(payload, "text")
        classifier = _load_task2_classifier()
        prediction = classifier(text)[0]
        return {
            "text": text,
            "prediction": prediction,
            "model_dir": str(TASK2_MODEL_DIR),
        }

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, request_path: str) -> None:
        relative = request_path.strip("/") or "index.html"
        if relative == "favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        path = _safe_child(CLIENT_DIR, relative)
        if path.is_dir():
            path = path / "index.html"
        if not path.exists():
            path = CLIENT_DIR / "index.html"
        self._send_file(path)

    def _serve_artifact(self, raw_path: str) -> None:
        if not raw_path:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing artifact path")
            return
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / path
        resolved = path.resolve()
        allowed_dirs = [
            (ROOT / "task1_financial" / "outputs").resolve(),
            (ROOT / "task3_agentic" / "outputs").resolve(),
        ]
        if not any(_is_relative_to(resolved, allowed) for allowed in allowed_dirs) or not resolved.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Artifact not found")
            return
        self._send_file(resolved)

    def _send_file(self, path: Path) -> None:
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


_TASK2_CLASSIFIER: Any | None = None


def _load_task2_classifier() -> Any:
    global _TASK2_CLASSIFIER
    if _TASK2_CLASSIFIER is not None:
        return _TASK2_CLASSIFIER
    if not TASK2_MODEL_DIR.exists():
        raise ValueError(f"Task 2 model not found at {TASK2_MODEL_DIR}")
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    except ImportError as exc:
        raise ValueError("Task 2 dependencies are missing. Install task2_finetuning/requirements-task2.txt") from exc

    TASK2_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(TASK2_MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(TASK2_MODEL_DIR)
    _TASK2_CLASSIFIER = pipeline("text-classification", model=model, tokenizer=tokenizer)
    return _TASK2_CLASSIFIER


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _safe_child(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not _is_relative_to(path, root.resolve()):
        raise ValueError("Invalid path")
    return path


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local React client and API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if not CLIENT_DIR.exists():
        raise SystemExit(f"Client directory not found: {CLIENT_DIR}")

    httpd = ThreadingHTTPServer((args.host, args.port), AppRequestHandler)
    print(f"React client available at http://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
