"""State and dependency contracts for the research supervisor."""

from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Annotated, Any, NotRequired, Protocol, Required, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages

from deep_research_langgraph.research.types import ResearchResult


class SupervisorInput(TypedDict):
    """Inputs accepted by the supervisor graph."""

    research_brief: str
    supervisor_messages: NotRequired[Sequence[BaseMessage]]
    max_supervisor_iterations: NotRequired[int]
    max_concurrent_researchers: NotRequired[int]
    max_search_iterations: NotRequired[int]
    max_results_per_query: NotRequired[int]


class SupervisorState(TypedDict, total=False):
    """State for the multi-agent research supervisor."""

    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]
    research_brief: Required[str]
    notes: Annotated[list[str], operator.add]
    research_iterations: int
    raw_notes: Annotated[list[str], operator.add]
    max_supervisor_iterations: int
    max_concurrent_researchers: int
    max_search_iterations: int
    max_results_per_query: int


class SupervisorResult(TypedDict, total=False):
    """Final result returned by the supervisor graph."""

    research_brief: Required[str]
    notes: list[str]
    raw_notes: list[str]
    research_iterations: int
    supervisor_messages: Sequence[BaseMessage]


class BoundSupervisorModelLike(Protocol):
    """Subset of a tool-bound chat model used by the supervisor."""

    async def ainvoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        """Generate the next supervisor message."""
        ...


class SupervisorModelLike(Protocol):
    """Subset of the chat model API needed by the supervisor."""

    def bind_tools(
        self,
        tools: Sequence[BaseTool],
        **kwargs: Any,
    ) -> BoundSupervisorModelLike:
        """Bind tools to the chat model."""
        ...


class ResearchAgentRunner(Protocol):
    """Contract for delegated researcher sub-agents."""

    async def run(
        self,
        research_topic: str,
        *,
        max_search_iterations: int,
        max_results_per_query: int,
    ) -> ResearchResult:
        """Run one isolated research task."""
        ...


__all__ = [
    "BoundSupervisorModelLike",
    "ResearchAgentRunner",
    "SupervisorInput",
    "SupervisorModelLike",
    "SupervisorResult",
    "SupervisorState",
]
