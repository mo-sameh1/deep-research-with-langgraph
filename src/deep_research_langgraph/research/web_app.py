"""Small browser app for the research agent."""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Literal, cast

from deep_research_langgraph.settings import get_settings

from .graph import (
    build_research_graph,
    create_default_research_app,
    create_default_research_services,
)
from .session import ResearchSession
from .tools import create_search_client
from .views import app_html, graph_html

SearchProvider = Literal["duckduckgo", "tavily", "auto"]


def run_graph_display(
    *,
    host: str = "127.0.0.1",
    port: int = 8771,
    open_browser: bool = True,
) -> None:
    """Start a local web display for the research graph."""

    server = ResearchGraphServer((host, port), ResearchGraphRequestHandler)
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Research graph display running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping research graph display.")
    finally:
        server.server_close()


def run_research_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8770,
    open_browser: bool = True,
    trace_enabled: bool | None = None,
    search_provider: SearchProvider | None = None,
) -> None:
    """Start the local research browser app."""

    server = ResearchAppServer(
        (host, port),
        ResearchRequestHandler,
        trace_enabled=trace_enabled,
        search_provider=search_provider,
    )
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Research app running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping research app.")
    finally:
        server.server_close()


class ResearchAppServer(ThreadingHTTPServer):
    """HTTP server that owns one research session."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        trace_enabled: bool | None = None,
        search_provider: SearchProvider | None = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.session = _create_research_session(search_provider=search_provider)
        self.trace_enabled = trace_enabled


class ResearchGraphServer(ThreadingHTTPServer):
    """HTTP server that owns research graph HTML."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
    ) -> None:
        super().__init__(server_address, request_handler_class)
        mermaid_graph = create_default_research_app().get_graph(xray=True).draw_mermaid()
        self.html = graph_html(mermaid_graph)


class ResearchGraphRequestHandler(BaseHTTPRequestHandler):
    """Serve the research graph page."""

    def do_GET(self) -> None:
        """Serve Mermaid graph HTML."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        graph_server = cast(ResearchGraphServer, self.server)
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


class ResearchRequestHandler(BaseHTTPRequestHandler):
    """Serve the app shell and research API."""

    def do_GET(self) -> None:
        """Serve the app shell."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_html(app_html())

    def do_POST(self) -> None:
        """Handle research requests."""

        if self.path != "/api/research":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            research_brief = str(payload.get("research_brief", "")).strip()
            if not research_brief:
                raise InvalidResearchPayload("research_brief is required.")
            max_iterations = int(payload.get("max_search_iterations", 2))
            max_results = int(payload.get("max_results_per_query", 3))
        except (ValueError, InvalidResearchPayload, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        app_server = cast(ResearchAppServer, self.server)
        result = app_server.session.run(
            research_brief,
            max_search_iterations=max_iterations,
            max_results_per_query=max_results,
            source="browser-app",
            trace_enabled=app_server.trace_enabled,
        )
        self._send_json(
            {
                "compressed_research": result.get("compressed_research", ""),
                "raw_notes": result.get("raw_notes", []),
                "key_sources": result.get("key_sources", []),
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while running."""

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise InvalidResearchPayload("Expected a JSON object.")
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


class InvalidResearchPayload(ValueError):
    """Raised when the research API receives invalid input."""


def _create_research_session(
    *,
    search_provider: SearchProvider | None = None,
) -> ResearchSession:
    if search_provider is None:
        return ResearchSession()

    settings = get_settings()
    search_client = create_search_client(
        provider=search_provider,
        tavily_api_key=settings.tavily_api_key,
        tavily_search_depth=settings.tavily_search_depth,
        tavily_include_answer=settings.tavily_include_answer,
        tavily_include_raw_content=settings.tavily_include_raw_content,
    )
    graph = build_research_graph(create_default_research_services(search_client=search_client))
    return ResearchSession(graph=graph)


__all__ = ["run_graph_display", "run_research_app"]
