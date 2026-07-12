"""Research search tools."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any, Final, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from tavily import TavilyClient

from deep_research_langgraph.langsmith.tracing import workflow_span
from deep_research_langgraph.settings import Settings, get_settings

from .types import SearchClient, SearchResult

USER_AGENT: Final[str] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


@dataclass(frozen=True)
class DuckDuckGoLiteSearchClient:
    """Free web search client using DuckDuckGo Lite HTML results."""

    timeout_seconds: float = 10.0
    fetch_pages: bool = True
    max_page_chars: int = 5000

    def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        """Return search results with snippets and optional fetched page text."""

        with workflow_span(
            name="local_web_search",
            run_type="tool",
            inputs={"query": query, "max_results": max_results},
            metadata={"provider": "duckduckgo_lite", "paid_api": False},
            tags=["tool:local_web_search", "provider:duckduckgo-lite"],
        ) as run:
            url = "https://lite.duckduckgo.com/lite/?" + urlencode({"q": query})
            html = _read_url(url, timeout_seconds=self.timeout_seconds)
            parser = DuckDuckGoLiteParser()
            parser.feed(html)

            results: list[SearchResult] = []
            seen_urls: set[str] = set()
            for parsed in parser.results:
                if parsed.url in seen_urls:
                    continue
                seen_urls.add(parsed.url)
                fetched_text = ""
                if self.fetch_pages:
                    fetched_text = _fetch_page_text(
                        parsed.url,
                        timeout_seconds=self.timeout_seconds,
                        max_chars=self.max_page_chars,
                    )
                results.append(
                    SearchResult(
                        title=parsed.title,
                        url=parsed.url,
                        snippet=parsed.snippet,
                        fetched_text=fetched_text,
                    )
                )
                if len(results) >= max_results:
                    break
            if run is not None:
                run.end(
                    outputs={
                        "result_count": len(results),
                        "urls": [result.url for result in results],
                    }
                )
            return results


@dataclass(frozen=True)
class TavilySearchClient:
    """Tavily-backed search client for higher quality research retrieval."""

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
                "paid_api": True,
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
    """Create the configured search client for the research graph."""

    resolved_settings = settings or get_settings()
    provider = resolved_settings.research_search_provider
    return create_search_client(
        provider=provider,
        tavily_api_key=resolved_settings.tavily_api_key,
        tavily_search_depth=resolved_settings.tavily_search_depth,
        tavily_include_answer=resolved_settings.tavily_include_answer,
        tavily_include_raw_content=resolved_settings.tavily_include_raw_content,
    )


def create_search_client(
    *,
    provider: Literal["duckduckgo", "tavily", "auto"],
    tavily_api_key: str | None,
    tavily_search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic",
    tavily_include_answer: bool = False,
    tavily_include_raw_content: bool = False,
) -> SearchClient:
    """Create a search client from explicit provider configuration."""

    if provider == "auto":
        provider = "tavily" if tavily_api_key else "duckduckgo"
    if provider == "duckduckgo":
        return DuckDuckGoLiteSearchClient()
    if not tavily_api_key:
        msg = "RESEARCH_SEARCH_PROVIDER=tavily requires TAVILY_API_KEY."
        raise ValueError(msg)
    return TavilySearchClient(
        api_key=tavily_api_key,
        search_depth=tavily_search_depth,
        include_answer=tavily_include_answer,
        include_raw_content=tavily_include_raw_content,
    )


@dataclass(frozen=True)
class ParsedSearchResult:
    """Internal parsed search result."""

    title: str
    url: str
    snippet: str


class DuckDuckGoLiteParser(HTMLParser):
    """Parse DuckDuckGo Lite result links and snippets."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[ParsedSearchResult] = []
        self._capturing_link = False
        self._capturing_snippet = False
        self._current_href = ""
        self._current_title: list[str] = []
        self._last_result_index: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")
        if tag == "a" and class_name == "result-link":
            self._capturing_link = True
            self._current_href = attrs_dict.get("href", "") or ""
            self._current_title = []
        elif tag == "td" and class_name == "result-snippet":
            self._capturing_snippet = True

    def handle_data(self, data: str) -> None:
        if self._capturing_link:
            self._current_title.append(data)
        elif self._capturing_snippet and self._last_result_index is not None:
            previous = self.results[self._last_result_index]
            snippet = " ".join((previous.snippet, data)).strip()
            self.results[self._last_result_index] = ParsedSearchResult(
                title=previous.title,
                url=previous.url,
                snippet=snippet,
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capturing_link:
            title = _normalize_whitespace(unescape("".join(self._current_title)))
            url = _extract_duckduckgo_url(self._current_href)
            if title and url:
                self.results.append(ParsedSearchResult(title=title, url=url, snippet=""))
                self._last_result_index = len(self.results) - 1
            self._capturing_link = False
        elif tag == "td" and self._capturing_snippet:
            self._capturing_snippet = False


class PageTextParser(HTMLParser):
    """Extract visible-ish text from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = _normalize_whitespace(unescape(data))
        if text:
            self.parts.append(text)

    def text(self, *, max_chars: int) -> str:
        """Return extracted text up to a character budget."""

        joined = _normalize_whitespace(" ".join(self.parts))
        return joined[:max_chars]


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


def _read_url(url: str, *, timeout_seconds: float) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout_seconds) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def _fetch_page_text(url: str, *, timeout_seconds: float, max_chars: int) -> str:
    try:
        html = _read_url(url, timeout_seconds=timeout_seconds)
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError):
        return ""
    parser = PageTextParser()
    parser.feed(html)
    return parser.text(max_chars=max_chars)


def _extract_duckduckgo_url(href: str) -> str:
    href = unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        values = parse_qs(parsed.query).get("uddg", [])
        return values[0] if values else ""
    return urljoin("https://lite.duckduckgo.com", href)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
