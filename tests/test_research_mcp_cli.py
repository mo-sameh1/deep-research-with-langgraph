from deep_research_langgraph.research_mcp.cli import build_parser, main


def test_mcp_run_parser_accepts_streaming_and_tool_budget() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "--stream",
            "--max-tool-iterations",
            "4",
            "What",
            "coffee",
            "shops?",
        ]
    )

    assert args.command == "run"
    assert args.stream is True
    assert args.max_tool_iterations == 4
    assert args.brief == ["What", "coffee", "shops?"]


def test_mcp_tools_parser_can_print_sample_dir() -> None:
    parser = build_parser()

    args = parser.parse_args(["tools", "--sample-dir"])

    assert args.command == "tools"
    assert args.sample_dir is True


def test_mcp_cli_without_command_returns_usage_error() -> None:
    assert main([]) == 2
