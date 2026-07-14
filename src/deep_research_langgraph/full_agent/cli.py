"""Command line interface for the full deep-research agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from langchain_core.messages import BaseMessage

from deep_research_langgraph.scope.streaming import iter_text_chunks

from .graph import create_default_full_agent_app
from .session import FullAgentSession
from .web_app import run_full_agent_app, run_graph_display


def main(argv: list[str] | None = None) -> int:
    """Run the full agent CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_command(args)
    if args.command == "display":
        return display_command(args)
    if args.command == "graph":
        return graph_command(args)
    if args.command == "app":
        return app_command(args)

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        prog="python -m deep_research_langgraph.full_agent",
        description="Run or display the full deep-research agent.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the full research workflow.")
    run_parser.add_argument("request", nargs="*", help="User research request.")
    run_parser.add_argument("--request-file", type=Path, help="Read the request from a file.")
    run_parser.add_argument("--max-supervisor-iterations", type=int, default=4)
    run_parser.add_argument("--max-concurrent-researchers", type=int, default=2)
    run_parser.add_argument("--max-search-iterations", type=int, default=1)
    run_parser.add_argument("--max-results-per-query", type=int, default=2)
    run_parser.add_argument("--stream", action="store_true")
    run_parser.add_argument("--stream-delay", type=float, default=0.01)
    _add_model_provider_argument(run_parser)
    run_parser.add_argument(
        "--trace",
        action="store_true",
        help="Send this run to LangSmith when LANGSMITH_API_KEY is configured.",
    )

    graph_parser = subparsers.add_parser("graph", help="Print or write Mermaid graph.")
    graph_parser.add_argument("--output", type=Path)
    _add_model_provider_argument(graph_parser)

    display_parser = subparsers.add_parser(
        "display", help="Open the full graph in a browser window."
    )
    display_parser.add_argument("--host", default="127.0.0.1")
    display_parser.add_argument("--port", type=int, default=8801)
    display_parser.add_argument("--no-open", action="store_true")
    _add_model_provider_argument(display_parser)

    app_parser = subparsers.add_parser("app", help="Start the full-agent browser app.")
    app_parser.add_argument("--host", default="127.0.0.1")
    app_parser.add_argument("--port", type=int, default=8800)
    app_parser.add_argument("--no-open", action="store_true")
    _add_model_provider_argument(app_parser)
    app_parser.add_argument(
        "--trace",
        action="store_true",
        help="Send browser app runs to LangSmith when LANGSMITH_API_KEY is configured.",
    )

    return parser


def run_command(args: argparse.Namespace) -> int:
    """Run the full research workflow and print the result."""

    request = _read_request(args)
    if not request:
        print("No research request provided.", file=sys.stderr)
        return 2

    try:
        graph = create_default_full_agent_app(model_provider=args.model_provider)
        result = asyncio.run(
            FullAgentSession(graph=graph).arun(
                request,
                max_supervisor_iterations=args.max_supervisor_iterations,
                max_concurrent_researchers=args.max_concurrent_researchers,
                max_search_iterations=args.max_search_iterations,
                max_results_per_query=args.max_results_per_query,
                trace_enabled=args.trace,
            )
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    final_report = result.get("final_report")
    if final_report is not None:
        print("\nFinal report:\n")
        _print_text(str(final_report), stream=args.stream, delay=args.stream_delay)
        return 0

    latest_message = _latest_message_content(result.get("messages", []))
    print("\nClarification needed:\n")
    _print_text(latest_message, stream=args.stream, delay=args.stream_delay)
    return 0


def graph_command(args: argparse.Namespace) -> int:
    """Render the graph as Mermaid text."""

    try:
        graph = create_default_full_agent_app(model_provider=args.model_provider).get_graph(
            xray=True
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    mermaid = graph.draw_mermaid()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(mermaid, encoding="utf-8")
        print(f"Wrote graph to {args.output}")
    else:
        print(mermaid)
    return 0


def display_command(args: argparse.Namespace) -> int:
    """Open the Mermaid graph in a browser window."""

    try:
        run_graph_display(
            host=args.host,
            port=args.port,
            open_browser=not args.no_open,
            model_provider=args.model_provider,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def app_command(args: argparse.Namespace) -> int:
    """Start the browser app."""

    try:
        run_full_agent_app(
            host=args.host,
            port=args.port,
            open_browser=not args.no_open,
            trace_enabled=args.trace,
            model_provider=args.model_provider,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _read_request(args: argparse.Namespace) -> str:
    if args.request_file:
        return args.request_file.read_text(encoding="utf-8").strip()
    return " ".join(args.request).strip()


def _add_model_provider_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model-provider",
        choices=["ollama", "groq"],
        default=None,
        help=(
            "Model backend for the full-agent path. Defaults to "
            "FULL_AGENT_MODEL_PROVIDER or local Ollama."
        ),
    )


def _print_text(text: str, *, stream: bool, delay: float) -> None:
    if not stream:
        print(text)
        return
    for chunk in iter_text_chunks(text):
        print(chunk, end="", flush=True)
        if delay > 0:
            time.sleep(delay)
    print()


def _latest_message_content(messages: object) -> str:
    if not isinstance(messages, list) or not messages:
        return ""
    message = messages[-1]
    if isinstance(message, BaseMessage):
        return str(message.content)
    return str(message)


if __name__ == "__main__":
    raise SystemExit(main())
