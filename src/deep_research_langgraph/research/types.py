"""Shared state and model contracts for the research agent."""

from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Annotated, Any, NotRequired, Protocol, Required, TypedDict, cast

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """One local web search result."""

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    snippet: str = ""
    fetched_text: str = ""

    def format_for_notes(self) -> str:
        """Format the result for LLM-readable observations."""

        content = self.fetched_text or self.snippet
        return f"Title: {self.title}\nURL: {self.url}\nContent: {content}".strip()


class ResearchDecision(BaseModel):
    """Structured decision from the research planning node."""

    reflection: str = Field(description="Assessment of current findings, gaps, and next step.")
    enough_information: bool = Field(
        description="Whether the agent should stop searching and compress findings."
    )
    search_queries: list[str] = Field(
        default_factory=list,
        description="Search queries to run next when more information is needed.",
    )


class SourceReference(BaseModel):
    """A source cited by the compressed research output."""

    title: str = ""
    url: str = ""
    relevance: str = ""


class CompressedResearch(BaseModel):
    """Structured compressed output from the research agent."""

    compressed_research: str = Field(
        min_length=1,
        description="Dense research notes for a downstream report writer.",
    )
    key_sources: list[SourceReference] = Field(default_factory=list)


class ResearchInput(TypedDict):
    """Required inputs for starting the research agent."""

    research_brief: str
    max_search_iterations: NotRequired[int]
    max_results_per_query: NotRequired[int]


class ResearchState(TypedDict, total=False):
    """LangGraph state for the research agent."""

    research_brief: Required[str]
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    search_iterations: int
    max_search_iterations: int
    max_results_per_query: int
    pending_search_queries: list[str]
    compressed_research: str
    key_sources: list[dict[str, str]]
    raw_notes: Annotated[list[str], operator.add]


class ResearchResult(TypedDict, total=False):
    """Final result returned by the research session."""

    research_brief: Required[str]
    compressed_research: Required[str]
    raw_notes: list[str]
    key_sources: list[dict[str, str]]
    researcher_messages: Sequence[BaseMessage]


class StructuredOutputRunnable(Protocol):
    """Subset of the structured-output runnable API used by this module."""

    def invoke(self, input: Sequence[BaseMessage] | str) -> BaseModel | dict[str, Any]:
        """Execute the structured output call."""
        ...


class ChatModelLike(Protocol):
    """Subset of the chat model API needed by the research nodes."""

    def invoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        """Generate a chat response."""
        ...

    def with_structured_output(
        self,
        schema: type[BaseModel],
        *,
        method: str = "json_schema",
        include_raw: bool = False,
        **kwargs: Any,
    ) -> StructuredOutputRunnable:
        """Return a runnable that yields structured data."""
        ...


class SearchClient(Protocol):
    """Search client contract used by the tool node."""

    def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        """Return search results for a query."""
        ...


def coerce_structured_output[T: BaseModel](
    output: BaseModel | dict[str, Any],
    schema: type[T],
) -> T:
    """Normalize structured-output responses from different model providers."""

    if isinstance(output, schema):
        return output
    if isinstance(output, BaseModel):
        return schema.model_validate(output.model_dump())
    return schema.model_validate(cast(dict[str, Any], output))
