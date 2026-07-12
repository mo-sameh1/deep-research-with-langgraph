"""Small browser app for the research supervisor."""

from __future__ import annotations

import asyncio
import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

from .graph import create_default_supervisor_app
from .session import ResearchSupervisorSession
from .views import app_html, graph_html


def run_graph_display(
    *,
    host: str = "127.0.0.1",
    port: int = 8791,
    open_browser: bool = True,
) -> None:
    """Start a local web display for the supervisor graph."""

    server = SupervisorGraphServer((host, port), SupervisorGraphRequestHandler)
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Research supervisor graph display running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping research supervisor graph display.")
    finally:
        server.server_close()


def run_supervisor_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8790,
    open_browser: bool = True,
    trace_enabled: bool | None = None,
) -> None:
    """Start the local supervisor browser app."""

    server = SupervisorAppServer(
        (host, port),
        SupervisorRequestHandler,
        trace_enabled=trace_enabled,
    )
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Research supervisor app running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping research supervisor app.")
    finally:
        server.server_close()


class SupervisorAppServer(ThreadingHTTPServer):
    """HTTP server that owns one supervisor session."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        trace_enabled: bool | None = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.session = ResearchSupervisorSession()
        self.trace_enabled = trace_enabled


class SupervisorGraphServer(ThreadingHTTPServer):
    """HTTP server that owns supervisor graph HTML."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
    ) -> None:
        super().__init__(server_address, request_handler_class)
        mermaid_graph = create_default_supervisor_app().get_graph(xray=True).draw_mermaid()
        self.html = graph_html(mermaid_graph)


class SupervisorGraphRequestHandler(BaseHTTPRequestHandler):
    """Serve the supervisor graph page."""

    def do_GET(self) -> None:
        """Serve Mermaid graph HTML."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        graph_server = cast(SupervisorGraphServer, self.server)
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


class SupervisorRequestHandler(BaseHTTPRequestHandler):
    """Serve the app shell and supervisor API."""

    def do_GET(self) -> None:
        """Serve the app shell."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_html(app_html())

    def do_POST(self) -> None:
        """Handle supervisor requests."""

        if self.path != "/api/supervisor":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            research_brief = str(payload.get("research_brief", "")).strip()
            if not research_brief:
                raise InvalidSupervisorPayload("research_brief is required.")
            max_supervisor_iterations = int(payload.get("max_supervisor_iterations", 6))
            max_concurrent_researchers = int(payload.get("max_concurrent_researchers", 3))
            max_search_iterations = int(payload.get("max_search_iterations", 2))
            max_results = int(payload.get("max_results_per_query", 3))
        except (ValueError, InvalidSupervisorPayload, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        app_server = cast(SupervisorAppServer, self.server)
        result = asyncio.run(
            app_server.session.arun(
                research_brief,
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
                "notes": result.get("notes", []),
                "raw_notes": result.get("raw_notes", []),
                "research_iterations": result.get("research_iterations", 0),
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while running."""

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise InvalidSupervisorPayload("Expected a JSON object.")
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


class InvalidSupervisorPayload(ValueError):
    """Raised when the supervisor API receives invalid input."""


__all__ = ["run_graph_display", "run_supervisor_app"]
