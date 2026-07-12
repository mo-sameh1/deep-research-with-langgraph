"""Small browser app for the scope workflow."""

from __future__ import annotations

import json
import tempfile
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import AIMessage

from .graph import create_default_scope_app
from .session import ScopeSession
from .views import app_html, graph_html


def open_graph_display(*, open_browser: bool = True) -> Path:
    """Render the scope graph to a temporary Mermaid HTML page."""

    mermaid_graph = create_default_scope_app().get_graph(xray=True).draw_mermaid()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix="-scope-graph.html",
        delete=False,
    ) as file:
        file.write(graph_html(mermaid_graph))
        path = Path(file.name)
    if open_browser:
        webbrowser.open(path.as_uri())
    return path


def run_scope_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """Start the local browser app."""

    server = ScopeAppServer((host, port), ScopeRequestHandler)
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Scope app running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping scope app.")
    finally:
        server.server_close()


class ScopeAppServer(ThreadingHTTPServer):
    """HTTP server that owns one scope session."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.session = ScopeSession()


class ScopeRequestHandler(BaseHTTPRequestHandler):
    """Serve the browser UI and message API."""

    def do_GET(self) -> None:
        """Serve the app shell."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_html(app_html())

    def do_POST(self) -> None:
        """Handle scope messages."""

        if self.path == "/api/message":
            self._handle_message()
            return
        if self.path == "/api/reset":
            scope_server = cast(ScopeAppServer, self.server)
            scope_server.session = ScopeSession()
            self._send_json({"ok": True})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while the browser app is running."""

    def _handle_message(self) -> None:
        try:
            content_length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self._send_json({"error": "Invalid JSON payload."}, HTTPStatus.BAD_REQUEST)
            return

        if not message:
            self._send_json({"error": "Message is required."}, HTTPStatus.BAD_REQUEST)
            return

        scope_server = cast(ScopeAppServer, self.server)
        scope_server.session.add_user_message(message)
        result = scope_server.session.run_turn()
        self._send_json(
            {
                "assistant_message": _latest_assistant_message(result["messages"]),
                "research_brief": result.get("research_brief"),
            }
        )

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


def _latest_assistant_message(messages: list[Any]) -> str | None:
    assistant_messages = [message for message in messages if isinstance(message, AIMessage)]
    if not assistant_messages:
        return None
    content = assistant_messages[-1].content
    return str(content) if content is not None else None


__all__ = ["open_graph_display", "run_scope_app"]
