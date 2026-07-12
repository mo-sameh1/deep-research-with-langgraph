"""Local, no-paid-API research tools."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from .types import SearchResult

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
        return results


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
