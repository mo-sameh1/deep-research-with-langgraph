"""Small browser app for the full deep-research agent."""

from __future__ import annotations

import asyncio
import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

from langchain_core.messages import BaseMessage

from .graph import create_default_full_agent_app
from .session import FullAgentSession
from .views import app_html, graph_html


def run_graph_display(
    *,
    host: str = "127.0.0.1",
    port: int = 8801,
    open_browser: bool = True,
    model_provider: str | None = None,
) -> None:
    """Start a local web display for the full graph."""

    server = FullAgentGraphServer(
        (host, port),
        FullAgentGraphRequestHandler,
        model_provider=model_provider,
    )
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Full agent graph display running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping full agent graph display.")
    finally:
        server.server_close()


def run_full_agent_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8800,
    open_browser: bool = True,
    trace_enabled: bool | None = None,
    model_provider: str | None = None,
) -> None:
    """Start the local full-agent browser app."""

    server = FullAgentAppServer(
        (host, port),
        FullAgentRequestHandler,
        trace_enabled=trace_enabled,
        model_provider=model_provider,
    )
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Full agent app running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping full agent app.")
    finally:
        server.server_close()


class FullAgentAppServer(ThreadingHTTPServer):
    """HTTP server that owns one full-agent session."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        trace_enabled: bool | None = None,
        model_provider: str | None = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        graph = create_default_full_agent_app(model_provider=model_provider)
        self.session = FullAgentSession(graph=graph)
        self.trace_enabled = trace_enabled


class FullAgentGraphServer(ThreadingHTTPServer):
    """HTTP server that owns full-agent graph HTML."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        model_provider: str | None = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        mermaid_graph = (
            create_default_full_agent_app(model_provider=model_provider)
            .get_graph(xray=True)
            .draw_mermaid()
        )
        self.html = graph_html(mermaid_graph)


class FullAgentGraphRequestHandler(BaseHTTPRequestHandler):
    """Serve the full graph page."""

    def do_GET(self) -> None:
        """Serve Mermaid graph HTML."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        graph_server = cast(FullAgentGraphServer, self.server)
        self._send_html(graph_server.html)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while running."""

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class FullAgentRequestHandler(BaseHTTPRequestHandler):
    """Serve the app shell and full-agent API."""

    def do_GET(self) -> None:
        """Serve the app shell."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_html(app_html())

    def do_POST(self) -> None:
        """Handle full-agent requests."""

        if self.path != "/api/full-agent":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            request = str(payload.get("request", "")).strip()
            if not request:
                raise InvalidFullAgentPayload("request is required.")
            max_supervisor_iterations = int(payload.get("max_supervisor_iterations", 4))
            max_concurrent_researchers = int(payload.get("max_concurrent_researchers", 2))
            max_search_iterations = int(payload.get("max_search_iterations", 1))
            max_results = int(payload.get("max_results_per_query", 2))
        except (ValueError, InvalidFullAgentPayload, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        app_server = cast(FullAgentAppServer, self.server)
        result = asyncio.run(
            app_server.session.arun(
                request,
                max_supervisor_iterations=max_supervisor_iterations,
                max_concurrent_researchers=max_concurrent_researchers,
                max_search_iterations=max_search_iterations,
                max_results_per_query=max_results,
                source="browser-app",
                trace_enabled=app_server.trace_enabled,
            )
        )
        self._send_json(
            {
                "final_report": result.get("final_report", ""),
                "research_brief": result.get("research_brief", ""),
                "notes": result.get("notes", []),
                "raw_notes": result.get("raw_notes", []),
                "latest_message": _latest_message_content(result.get("messages", [])),
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while running."""

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise InvalidFullAgentPayload("Expected a JSON object.")
        return payload

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _latest_message_content(messages: object) -> str:
    if not isinstance(messages, list) or not messages:
        return ""
    message = messages[-1]
    if isinstance(message, BaseMessage):
        return str(message.content)
    return str(message)


class InvalidFullAgentPayload(ValueError):
    """Raised when the full-agent API receives invalid input."""


__all__ = ["run_full_agent_app", "run_graph_display"]
