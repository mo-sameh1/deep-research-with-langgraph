from deep_research_langgraph.research_supervisor.cli import build_parser, main


def test_supervisor_run_parser_accepts_budgets_and_streaming() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "run",
            "--stream",
            "--max-supervisor-iterations",
            "4",
            "--max-concurrent-researchers",
            "3",
            "--max-search-iterations",
            "1",
            "--max-results-per-query",
            "2",
            "Compare",
            "agents",
        ]
    )

    assert args.command == "run"
    assert args.stream is True
    assert args.max_supervisor_iterations == 4
    assert args.max_concurrent_researchers == 3
    assert args.max_search_iterations == 1
    assert args.max_results_per_query == 2
    assert args.brief == ["Compare", "agents"]


def test_supervisor_display_parser_accepts_no_open() -> None:
    parser = build_parser()

    args = parser.parse_args(["display", "--no-open", "--compiled"])

    assert args.command == "display"
    assert args.no_open is True
    assert args.compiled is True


def test_supervisor_graph_parser_defaults_to_expanded_view() -> None:
    parser = build_parser()

    args = parser.parse_args(["graph"])

    assert args.command == "graph"
    assert args.compiled is False


def test_supervisor_cli_without_command_returns_usage_error() -> None:
    assert main([]) == 2
