"""Tavily-backed research search tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from tavily import TavilyClient

from deep_research_langgraph.langsmith.tracing import workflow_span
from deep_research_langgraph.settings import Settings, get_settings

from .types import SearchClient, SearchResult


@dataclass(frozen=True)
class TavilySearchClient:
    """Tavily-backed search client for the research agent."""

    api_key: str
    timeout_seconds: float = 60.0
    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic"
    include_answer: bool = False
    include_raw_content: bool = False

    def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        """Return Tavily search results normalized to the research graph contract."""

        with workflow_span(
            name="tavily_search",
            run_type="tool",
            inputs={"query": query, "max_results": max_results},
            metadata={
                "provider": "tavily",
                "search_depth": self.search_depth,
                "include_answer": self.include_answer,
                "include_raw_content": self.include_raw_content,
            },
            tags=["tool:tavily_search", "provider:tavily"],
        ) as run:
            client = TavilyClient(api_key=self.api_key)
            response = client.search(
                query,
                search_depth=self.search_depth,
                max_results=max_results,
                include_answer=self.include_answer,
                include_raw_content=self.include_raw_content,
                include_usage=True,
                timeout=self.timeout_seconds,
            )
            results = _parse_tavily_results(response)
            if run is not None:
                run.end(
                    outputs={
                        "result_count": len(results),
                        "urls": [result.url for result in results],
                        "request_id": response.get("request_id"),
                        "usage": response.get("usage"),
                    }
                )
            return results


def create_search_client_from_settings(settings: Settings | None = None) -> SearchClient:
    """Create the Tavily search client configured for the research graph."""

    resolved_settings = settings or get_settings()
    return create_search_client(
        tavily_api_key=resolved_settings.tavily_api_key,
        tavily_search_depth=resolved_settings.tavily_search_depth,
        tavily_include_answer=resolved_settings.tavily_include_answer,
        tavily_include_raw_content=resolved_settings.tavily_include_raw_content,
    )


def create_search_client(
    *,
    tavily_api_key: str | None,
    tavily_search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic",
    tavily_include_answer: bool = False,
    tavily_include_raw_content: bool = False,
) -> SearchClient:
    """Create a Tavily search client from explicit configuration."""

    if not tavily_api_key:
        msg = "TAVILY_API_KEY is required for the research agent."
        raise ValueError(msg)
    return TavilySearchClient(
        api_key=tavily_api_key,
        search_depth=tavily_search_depth,
        include_answer=tavily_include_answer,
        include_raw_content=tavily_include_raw_content,
    )


def format_search_observation(query: str, results: list[SearchResult]) -> str:
    """Format search results for the research graph."""

    if not results:
        return f"Search query: {query}\nNo results found."

    sections = [f"Search query: {query}"]
    for index, result in enumerate(results, start=1):
        sections.append(f"\n--- SOURCE {index} ---\n{result.format_for_notes()}")
    return "\n".join(sections)


def think_tool(reflection: str) -> str:
    """Record a strategic research reflection."""

    return f"Reflection recorded: {reflection}"


def _parse_tavily_results(response: dict[str, Any]) -> list[SearchResult]:
    raw_results = response.get("results", [])
    if not isinstance(raw_results, list):
        return []

    results: list[SearchResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        url = _optional_string(item.get("url"))
        if not url:
            continue
        title = _optional_string(item.get("title")) or url
        content = _optional_string(item.get("content")) or ""
        raw_content = _optional_string(item.get("raw_content")) or ""
        results.append(
            SearchResult(
                title=title,
                url=url,
                snippet=content,
                fetched_text=raw_content,
            )
        )
    return results


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
