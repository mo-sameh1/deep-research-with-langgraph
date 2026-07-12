"""Command line interface for the scope workflow."""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

from langchain_core.messages import AIMessage

from .graph import create_default_scope_app
from .session import ScopeSession
from .types import ScopeResult
from .web_app import open_graph_display, run_scope_app


def main(argv: list[str] | None = None) -> int:
    """Run the scope workflow CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_scope_command(args)
    if args.command == "graph":
        return graph_command(args)
    if args.command == "display":
        return display_command(args)
    if args.command == "app":
        return app_command(args)

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        prog="python -m deep_research_langgraph.scope",
        description="Run or display the deep research scope graph.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Run the scoping interaction and generate a research brief.",
    )
    run_parser.add_argument(
        "request",
        nargs="*",
        help="Initial research request. If omitted, the CLI prompts for it.",
    )
    run_parser.add_argument(
        "--max-clarifications",
        type=int,
        default=2,
        help="Maximum number of follow-up clarification turns to allow.",
    )

    graph_parser = subparsers.add_parser(
        "graph",
        help="Print the graph as Mermaid or write Mermaid/PNG to a file.",
    )
    graph_parser.add_argument(
        "--output",
        type=Path,
        help="Output path. Use .png for an image, otherwise Mermaid text is written.",
    )

    display_parser = subparsers.add_parser(
        "display",
        help="Open the scope graph in a browser window using Mermaid.",
    )
    display_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Create the temporary HTML file without opening a browser.",
    )

    app_parser = subparsers.add_parser(
        "app",
        help="Start a small local browser app for the scoping interaction.",
    )
    app_parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    app_parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    app_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Start the server without opening a browser.",
    )

    return parser


def run_scope_command(args: argparse.Namespace) -> int:
    """Run an interactive scoping session."""

    initial_request = " ".join(args.request).strip()
    if not initial_request:
        initial_request = input("Research request: ").strip()
    if not initial_request:
        print("No research request provided.", file=sys.stderr)
        return 2

    session = ScopeSession()
    session.add_user_message(initial_request)

    clarification_turns = 0
    while True:
        result = session.run_turn()
        _print_latest_assistant_message(result)
        research_brief = result.get("research_brief")
        if research_brief:
            print("\nResearch brief:\n")
            print(textwrap.fill(research_brief, width=100))
            return 0

        if clarification_turns >= args.max_clarifications:
            print(
                "\nStopped before generating a brief because the clarification limit was reached.",
                file=sys.stderr,
            )
            return 1

        clarification_turns += 1
        answer = input("\nYour answer: ").strip()
        if not answer:
            print("No clarification answer provided.", file=sys.stderr)
            return 2
        session.add_user_message(answer)


def graph_command(args: argparse.Namespace) -> int:
    """Render the compiled graph as Mermaid text or PNG."""

    graph = create_default_scope_app().get_graph(xray=True)
    output: Path | None = args.output
    if output is None:
        print(graph.draw_mermaid())
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".png":
        output.write_bytes(graph.draw_mermaid_png())
    else:
        output.write_text(graph.draw_mermaid(), encoding="utf-8")
    print(f"Wrote graph to {output}")
    return 0


def display_command(args: argparse.Namespace) -> int:
    """Open the Mermaid graph in a browser window."""

    path = open_graph_display(open_browser=not args.no_open)
    print(f"Opened graph display: {path}")
    return 0


def app_command(args: argparse.Namespace) -> int:
    """Start the browser app."""

    run_scope_app(host=args.host, port=args.port, open_browser=not args.no_open)
    return 0


def _print_latest_assistant_message(result: ScopeResult) -> None:
    messages = result["messages"]
    assistant_messages = [message for message in messages if isinstance(message, AIMessage)]
    if assistant_messages:
        print(f"\nAssistant:\n{assistant_messages[-1].content}")


if __name__ == "__main__":
    raise SystemExit(main())
