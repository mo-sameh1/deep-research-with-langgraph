from deep_research_langgraph.research.tools import (
    TavilySearchClient,
    _parse_tavily_results,
    create_search_client,
    format_search_observation,
)
from deep_research_langgraph.research.types import SearchResult


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


def test_create_search_client_uses_tavily_when_configured() -> None:
    client = create_search_client(
        tavily_api_key="tvly-test",
        tavily_search_depth="basic",
        tavily_include_answer=False,
        tavily_include_raw_content=False,
    )

    assert isinstance(client, TavilySearchClient)
    assert client.api_key == "tvly-test"


def test_create_search_client_requires_tavily_key() -> None:
    try:
        create_search_client(tavily_api_key=None)
    except ValueError as exc:
        assert "TAVILY_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected Tavily client without key to fail")


def test_parse_tavily_results_normalizes_response() -> None:
    results = _parse_tavily_results(
        {
            "results": [
                {
                    "title": "LangGraph docs",
                    "url": "https://langchain-ai.github.io/langgraph/",
                    "content": "LangGraph supports persistence.",
                    "raw_content": "Longer extracted page text.",
                }
            ]
        }
    )

    assert results == [
        SearchResult(
            title="LangGraph docs",
            url="https://langchain-ai.github.io/langgraph/",
            snippet="LangGraph supports persistence.",
            fetched_text="Longer extracted page text.",
        )
    ]
