"""Small browser app for the scope workflow."""

from __future__ import annotations

import json
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

from langchain_core.messages import AIMessage

from .graph import create_default_scope_app
from .session import ScopeSession
from .streaming import iter_text_chunks
from .views import app_html, graph_html


def run_graph_display(
    *,
    host: str = "127.0.0.1",
    port: int = 8767,
    open_browser: bool = True,
) -> None:
    """Start a local web display for the Mermaid graph."""

    server = GraphDisplayServer((host, port), GraphDisplayRequestHandler)
    url = f"http://{host}:{server.server_port}/"
    if open_browser:
        webbrowser.open(url)
    print(f"Scope graph display running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping scope graph display.")
    finally:
        server.server_close()


def run_scope_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    stream: bool = False,
    stream_delay: float = 0.015,
) -> None:
    """Start the local browser app."""

    server = ScopeAppServer(
        (host, port),
        ScopeRequestHandler,
        stream_enabled=stream,
        stream_delay=stream_delay,
    )
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
        *,
        stream_enabled: bool = False,
        stream_delay: float = 0.015,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.session = ScopeSession()
        self.stream_enabled = stream_enabled
        self.stream_delay = stream_delay

    def reset_session(self) -> None:
        """Start a fresh scoping session."""

        self.session = ScopeSession()


class GraphDisplayServer(ThreadingHTTPServer):
    """HTTP server that owns the Mermaid graph HTML."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
    ) -> None:
        super().__init__(server_address, request_handler_class)
        mermaid_graph = create_default_scope_app().get_graph(xray=True).draw_mermaid()
        self.html = graph_html(mermaid_graph)


class GraphDisplayRequestHandler(BaseHTTPRequestHandler):
    """Serve the graph display page."""

    def do_GET(self) -> None:
        """Serve the Mermaid graph page."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        display_server = cast(GraphDisplayServer, self.server)
        encoded = display_server.html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while the graph display is running."""


class ScopeRequestHandler(BaseHTTPRequestHandler):
    """Serve the browser UI and message API."""

    def do_GET(self) -> None:
        """Serve the app shell."""

        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        scope_server = cast(ScopeAppServer, self.server)
        self._send_html(app_html(streaming_enabled=scope_server.stream_enabled))

    def do_POST(self) -> None:
        """Handle scope messages."""

        if self.path == "/api/message":
            self._handle_message()
            return
        if self.path == "/api/message/stream":
            self._handle_stream_message()
            return
        if self.path == "/api/reset":
            scope_server = cast(ScopeAppServer, self.server)
            scope_server.reset_session()
            self._send_json({"ok": True})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal clean while the browser app is running."""

    def _handle_message(self) -> None:
        try:
            message = self._read_message_payload()
        except InvalidMessagePayload as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
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

    def _handle_stream_message(self) -> None:
        try:
            message = self._read_message_payload()
        except InvalidMessagePayload as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        scope_server = cast(ScopeAppServer, self.server)
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "application/x-ndjson")
        self.send_header("cache-control", "no-cache")
        self.end_headers()

        try:
            self._send_stream_event("status", text="Thinking locally with Ollama...")
            scope_server.session.add_user_message(message)
            result = scope_server.session.run_turn()
            assistant_message = _latest_assistant_message(result["messages"])
            if assistant_message:
                self._send_stream_event("assistant_start")
                self._send_text_deltas(assistant_message, delay=scope_server.stream_delay)
            research_brief = result.get("research_brief")
            if research_brief:
                self._send_stream_event("brief_start")
                self._send_text_deltas(research_brief, delay=scope_server.stream_delay)
            self._send_stream_event("done", has_research_brief=bool(research_brief))
        except Exception as exc:
            self._send_stream_event("error", text=str(exc))

    def _read_message_payload(self) -> str:
        try:
            content_length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
        except (ValueError, json.JSONDecodeError) as exc:
            raise InvalidMessagePayload("Invalid JSON payload.") from exc

        if not message:
            raise InvalidMessagePayload("Message is required.")
        return message

    def _send_text_deltas(self, text: str, *, delay: float) -> None:
        for chunk in iter_text_chunks(text):
            self._send_stream_event("delta", text=chunk)
            if delay > 0:
                time.sleep(delay)

    def _send_stream_event(self, event: str, **payload: Any) -> None:
        encoded = json.dumps({"event": event, **payload}).encode("utf-8") + b"\n"
        self.wfile.write(encoded)
        self.wfile.flush()

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


class InvalidMessagePayload(ValueError):
    """Raised when an API request does not contain a usable message."""


__all__ = ["run_graph_display", "run_scope_app"]
