"""Command line interface for the MCP research agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from deep_research_langgraph.scope.streaming import iter_text_chunks

from .config import create_mcp_client, get_sample_files_dir
from .graph import create_default_mcp_research_app
from .nodes import get_all_tools
from .session import MCPResearchSession
from .web_app import run_graph_display, run_mcp_research_app


def main(argv: list[str] | None = None) -> int:
    """Run the MCP research agent CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_command(args)
    if args.command == "tools":
        return tools_command(args)
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
        prog="python -m deep_research_langgraph.research_mcp",
        description="Run or display the MCP local-file research agent.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run MCP research for a question.")
    run_parser.add_argument("brief", nargs="*", help="Local-file research question.")
    run_parser.add_argument("--brief-file", type=Path, help="Read the question from a file.")
    run_parser.add_argument("--max-tool-iterations", type=int, default=6)
    run_parser.add_argument("--stream", action="store_true")
    run_parser.add_argument("--stream-delay", type=float, default=0.01)
    run_parser.add_argument(
        "--trace",
        action="store_true",
        help="Send this run to LangSmith when LANGSMITH_API_KEY is configured.",
    )

    tools_parser = subparsers.add_parser("tools", help="List available MCP tools.")
    tools_parser.add_argument(
        "--sample-dir",
        action="store_true",
        help="Print the local directory exposed to the filesystem MCP server.",
    )

    graph_parser = subparsers.add_parser("graph", help="Print or write Mermaid graph.")
    graph_parser.add_argument("--output", type=Path)

    display_parser = subparsers.add_parser(
        "display", help="Open the MCP graph in a browser window."
    )
    display_parser.add_argument("--host", default="127.0.0.1")
    display_parser.add_argument("--port", type=int, default=8781)
    display_parser.add_argument("--no-open", action="store_true")

    app_parser = subparsers.add_parser("app", help="Start the MCP research browser app.")
    app_parser.add_argument("--host", default="127.0.0.1")
    app_parser.add_argument("--port", type=int, default=8780)
    app_parser.add_argument("--no-open", action="store_true")
    app_parser.add_argument(
        "--trace",
        action="store_true",
        help="Send browser app runs to LangSmith when LANGSMITH_API_KEY is configured.",
    )

    return parser


def run_command(args: argparse.Namespace) -> int:
    """Run MCP local-file research and print compressed notes."""

    brief = _read_brief(args)
    if not brief:
        print("No MCP research question provided.", file=sys.stderr)
        return 2

    try:
        result = MCPResearchSession().run(
            brief,
            max_tool_call_iterations=args.max_tool_iterations,
            trace_enabled=args.trace,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    compressed = result.get("compressed_research", "")
    raw_notes = result.get("raw_notes", [])
    print("\nCompressed MCP research:\n")
    _print_text(compressed, stream=args.stream, delay=args.stream_delay)
    if raw_notes:
        print("\nRaw notes:\n")
        _print_text("\n\n".join(raw_notes), stream=args.stream, delay=args.stream_delay)
    return 0


def tools_command(args: argparse.Namespace) -> int:
    """List MCP tools exposed by the filesystem server."""

    if args.sample_dir:
        print(f"Sample files directory: {get_sample_files_dir()}")
    tools = asyncio.run(get_all_tools(create_mcp_client))
    for tool in tools:
        description = (tool.description or "").strip().splitlines()[0]
        print(f"- {tool.name}: {description}")
    return 0


def graph_command(args: argparse.Namespace) -> int:
    """Render the graph as Mermaid text."""

    graph = create_default_mcp_research_app().get_graph(xray=True)
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

    run_graph_display(host=args.host, port=args.port, open_browser=not args.no_open)
    return 0


def app_command(args: argparse.Namespace) -> int:
    """Start the browser app."""

    run_mcp_research_app(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        trace_enabled=args.trace,
    )
    return 0


def _read_brief(args: argparse.Namespace) -> str:
    if args.brief_file:
        return args.brief_file.read_text(encoding="utf-8").strip()
    return " ".join(args.brief).strip()


def _print_text(text: str, *, stream: bool, delay: float) -> None:
    if not stream:
        print(text)
        return
    for chunk in iter_text_chunks(text):
        print(chunk, end="", flush=True)
        if delay > 0:
            time.sleep(delay)
    print()


if __name__ == "__main__":
    raise SystemExit(main())
