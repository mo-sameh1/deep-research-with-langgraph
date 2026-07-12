from deep_research_langgraph.research.tools import (
    DuckDuckGoLiteParser,
    DuckDuckGoLiteSearchClient,
    TavilySearchClient,
    create_search_client,
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


def test_create_search_client_defaults_to_duckduckgo() -> None:
    client = create_search_client(provider="duckduckgo", tavily_api_key=None)

    assert isinstance(client, DuckDuckGoLiteSearchClient)


def test_create_search_client_uses_tavily_when_configured() -> None:
    client = create_search_client(
        provider="tavily",
        tavily_api_key="tvly-test",
        tavily_search_depth="basic",
        tavily_include_answer=False,
        tavily_include_raw_content=False,
    )

    assert isinstance(client, TavilySearchClient)
    assert client.api_key == "tvly-test"


def test_create_search_client_requires_tavily_key() -> None:
    try:
        create_search_client(provider="tavily", tavily_api_key=None)
    except ValueError as exc:
        assert "TAVILY_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected Tavily provider without key to fail")
