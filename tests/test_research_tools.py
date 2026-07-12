from deep_research_langgraph.research.tools import (
    DuckDuckGoLiteParser,
    format_search_observation,
)
from deep_research_langgraph.research.types import SearchResult


def test_duckduckgo_lite_parser_extracts_result_and_snippet() -> None:
    parser = DuckDuckGoLiteParser()

    parser.feed(
        """
        <a rel="nofollow"
           href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdoc"
           class='result-link'>Example Result</a>
        <td class='result-snippet'>A useful snippet.</td>
        """
    )

    assert parser.results[0].title == "Example Result"
    assert parser.results[0].url == "https://example.com/doc"
    assert parser.results[0].snippet == "A useful snippet."


def test_format_search_observation_includes_sources() -> None:
    observation = format_search_observation(
        "example query",
        [
            SearchResult(
                title="Example",
                url="https://example.com",
                snippet="Snippet",
            )
        ],
    )

    assert "Search query: example query" in observation
    assert "https://example.com" in observation
