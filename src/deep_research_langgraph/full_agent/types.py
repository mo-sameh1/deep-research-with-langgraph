"""State and model contracts for the full deep-research agent."""

from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Annotated, NotRequired, Protocol

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages


class FullAgentInputState(MessagesState):
    """Input state for the full agent."""

    max_supervisor_iterations: NotRequired[int]
    max_concurrent_researchers: NotRequired[int]
    max_search_iterations: NotRequired[int]
    max_results_per_query: NotRequired[int]


class FullAgentState(MessagesState):
    """State for the complete research workflow."""

    research_brief: str
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]
    raw_notes: Annotated[list[str], operator.add]
    notes: Annotated[list[str], operator.add]
    final_report: str
    max_supervisor_iterations: int
    max_concurrent_researchers: int
    max_search_iterations: int
    max_results_per_query: int


class WriterModelLike(Protocol):
    """Subset of the chat model API needed by final report generation."""

    async def ainvoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        """Generate a final report message."""
        ...


__all__ = ["FullAgentInputState", "FullAgentState", "WriterModelLike"]
