"""Node implementations for the research agent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, cast

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, get_buffer_string

from deep_research_langgraph.scope.dates import get_today_str

from .prompts import COMPRESS_RESEARCH_PROMPT, RESEARCH_AGENT_PROMPT
from .tools import format_search_observation, think_tool
from .types import (
    ChatModelLike,
    CompressedResearch,
    ResearchDecision,
    ResearchState,
    SearchClient,
    SourceReference,
    coerce_structured_output,
)


@dataclass(frozen=True)
class ResearchServices:
    """External dependencies used by research nodes."""

    llm: ChatModelLike
    search_client: SearchClient


@dataclass(frozen=True)
class ResearchPlannerNode:
    """Decide whether to search more or compress the research."""

    services: ResearchServices

    def __call__(self, state: ResearchState) -> ResearchState:
        max_iterations = state.get("max_search_iterations", 2)
        current_iteration = state.get("search_iterations", 0)
        if current_iteration >= max_iterations:
            return cast(
                ResearchState,
                {
                    "pending_search_queries": [],
                    "researcher_messages": [
                        AIMessage(
                            content=(
                                "Search iteration budget reached. "
                                "Compressing the gathered research."
                            )
                        )
                    ],
                },
            )

        structured_llm = self.services.llm.with_structured_output(
            ResearchDecision,
            method="json_schema",
        )
        prompt = RESEARCH_AGENT_PROMPT.format(
            date=get_today_str(),
            research_brief=state["research_brief"],
            messages=get_buffer_string(state.get("researcher_messages", [])),
            max_search_iterations=max_iterations,
        )
        decision = coerce_structured_output(
            structured_llm.invoke([HumanMessage(content=prompt)]),
            ResearchDecision,
        )

        queries = [query.strip() for query in decision.search_queries if query.strip()]
        if decision.enough_information:
            queries = []

        return cast(
            ResearchState,
            {
                "pending_search_queries": queries[:2],
                "researcher_messages": [AIMessage(content=think_tool(decision.reflection))],
            },
        )


@dataclass(frozen=True)
class SearchToolNode:
    """Execute local web searches selected by the planning node."""

    services: ResearchServices

    def __call__(self, state: ResearchState) -> ResearchState:
        queries = state.get("pending_search_queries", [])
        max_results = state.get("max_results_per_query", 3)
        messages: list[ToolMessage] = []
        raw_notes: list[str] = []

        for index, query in enumerate(queries, start=1):
            results = self.services.search_client.search(query, max_results=max_results)
            observation = format_search_observation(query, results)
            raw_notes.append(observation)
            messages.append(
                ToolMessage(
                    content=observation,
                    name="tavily_search",
                    tool_call_id=f"search-{state.get('search_iterations', 0)}-{index}",
                )
            )

        return cast(
            ResearchState,
            {
                "researcher_messages": messages,
                "raw_notes": raw_notes,
                "search_iterations": state.get("search_iterations", 0) + 1,
                "pending_search_queries": [],
            },
        )


@dataclass(frozen=True)
class CompressResearchNode:
    """Compress gathered observations into notes for the report writer."""

    services: ResearchServices

    def __call__(self, state: ResearchState) -> ResearchState:
        structured_llm = self.services.llm.with_structured_output(
            CompressedResearch,
            method="json_schema",
        )
        prompt = COMPRESS_RESEARCH_PROMPT.format(
            date=get_today_str(),
            research_brief=state["research_brief"],
            messages=get_buffer_string(state.get("researcher_messages", [])),
        )
        compressed = coerce_structured_output(
            structured_llm.invoke([HumanMessage(content=prompt)]),
            CompressedResearch,
        )
        compressed_research = compressed.compressed_research
        if len(compressed_research.strip()) < 160 and state.get("raw_notes"):
            compressed_research = _fallback_compressed_research(state)
        key_sources = compressed.key_sources or _extract_source_references(
            state.get("raw_notes", [])
        )
        return cast(
            ResearchState,
            {
                "compressed_research": compressed_research,
                "key_sources": [
                    cast(dict[str, str], source.model_dump()) for source in key_sources
                ],
            },
        )


def should_continue(state: ResearchState) -> Literal["tool_node", "compress_research"]:
    """Route to search tools when queries are pending, otherwise compress."""

    if state.get("pending_search_queries"):
        return "tool_node"
    return "compress_research"


def _fallback_compressed_research(state: ResearchState) -> str:
    """Create an extractive compressed summary when the LLM output is too terse."""

    raw_notes = state.get("raw_notes", [])
    source_refs = _extract_source_references(raw_notes)
    source_lines = [f"- {source.title}: {source.url}" for source in source_refs[:6] if source.url]
    evidence = "\n\n".join(raw_notes)[:5000]
    return "\n".join(
        [
            "Research findings gathered from local web search.",
            "",
            "Research brief:",
            state["research_brief"],
            "",
            "Key sources:",
            *(source_lines or ["- No sources were captured."]),
            "",
            "Evidence notes:",
            evidence,
        ]
    )


def _extract_source_references(raw_notes: list[str]) -> list[SourceReference]:
    """Extract title and URL pairs from formatted raw notes."""

    joined = "\n".join(raw_notes)
    matches = re.findall(r"Title: (?P<title>.+?)\nURL: (?P<url>\S+)", joined)
    return [
        SourceReference(title=title.strip(), url=url.strip(), relevance="Search result")
        for title, url in matches
    ]


__all__ = [
    "CompressResearchNode",
    "ResearchPlannerNode",
    "ResearchServices",
    "SearchToolNode",
    "should_continue",
]
