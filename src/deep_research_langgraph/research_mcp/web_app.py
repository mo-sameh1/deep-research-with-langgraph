"""Small browser app for the MCP research agent."""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

from .graph import create_default_mcp_research_app
from .session import MCPResearchSession
from .views import app_html, graph_html


def run_graph_display(
    *,
    host: str = "127.0.0.1",
    port: int = 8781,
    open_browser: bool = True,
) -> None:
    """Start a local web display for the MCP graph."""

    server = MCPResearchGraphServer((host, port), MCPResearchGraphRequestHandler)
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"MCP research graph display running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping MCP research graph display.")
    finally:
        server.server_close()


def run_mcp_research_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8780,
    open_browser: bool = True,
    trace_enabled: bool | None = None,
) -> None:
    """Start the local MCP research browser app."""

    server = MCPResearchAppServer(
        (host, port),
        MCPResearchRequestHandler,
        trace_enabled=trace_enabled,
    )
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"MCP research app running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping MCP research app.")
    finally:
        server.server_close()


class MCPResearchAppServer(ThreadingHTTPServer):
    """HTTP server that owns one MCP research session."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        trace_enabled: bool | None = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.session = MCPResearchSession()
        self.trace_enabled = trace_enabled


class MCPResearchGraphServer(ThreadingHTTPServer):
    """HTTP server that owns MCP research graph HTML."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
    ) -> None:
        super().__init__(server_address, request_handler_class)
        mermaid_graph = create_default_mcp_research_app().get_graph(xray=True).draw_mermaid()
        self.html = graph_html(mermaid_graph)


class MCPResearchGraphRequestHandler(BaseHTTPRequestHandler):
    """Serve the MCP graph page."""

    def do_GET(self) -> None:
        """Serve Mermaid graph HTML."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        graph_server = cast(MCPResearchGraphServer, self.server)
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


class MCPResearchRequestHandler(BaseHTTPRequestHandler):
    """Serve the app shell and MCP research API."""

    def do_GET(self) -> None:
        """Serve the app shell."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_html(app_html())

    def do_POST(self) -> None:
        """Handle MCP research requests."""

        if self.path != "/api/research":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            research_brief = str(payload.get("research_brief", "")).strip()
            if not research_brief:
                raise InvalidMCPResearchPayload("research_brief is required.")
            max_iterations = int(payload.get("max_tool_call_iterations", 6))
        except (ValueError, InvalidMCPResearchPayload, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        app_server = cast(MCPResearchAppServer, self.server)
        try:
            result = app_server.session.run(
                research_brief,
                max_tool_call_iterations=max_iterations,
                source="browser-app",
                trace_enabled=app_server.trace_enabled,
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(
            {
                "compressed_research": result.get("compressed_research", ""),
                "raw_notes": result.get("raw_notes", []),
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while running."""

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise InvalidMCPResearchPayload("Expected a JSON object.")
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


class InvalidMCPResearchPayload(ValueError):
    """Raised when the MCP research API receives invalid input."""


__all__ = ["run_graph_display", "run_mcp_research_app"]
