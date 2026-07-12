"""Shared contracts for the MCP research agent."""

from __future__ import annotations

import operator
from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated, Any, NotRequired, Protocol, Required, TypedDict, cast

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class MCPResearchInput(TypedDict):
    """Input state for starting the MCP research agent."""

    research_brief: str
    max_tool_call_iterations: NotRequired[int]


class MCPResearchState(TypedDict, total=False):
    """LangGraph state for MCP local-file research."""

    research_brief: Required[str]
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    tool_call_iterations: int
    max_tool_call_iterations: int
    compressed_research: str
    raw_notes: Annotated[list[str], operator.add]


class MCPResearchResult(TypedDict, total=False):
    """Final output from the MCP research agent."""

    research_brief: Required[str]
    compressed_research: Required[str]
    tool_call_iterations: int
    raw_notes: list[str]
    researcher_messages: Sequence[BaseMessage]


class CompressedMCPResearch(BaseModel):
    """Structured compressed output from MCP research."""

    compressed_research: str = Field(
        min_length=1,
        description="Dense local-file research notes for a downstream report writer.",
    )


class StructuredOutputRunnable(Protocol):
    """Subset of the structured-output runnable API used by this module."""

    def invoke(self, input: Sequence[BaseMessage] | str) -> BaseModel | dict[str, Any]:
        """Execute the structured output call."""
        ...


class BoundToolModelLike(Protocol):
    """Model returned after binding MCP tools."""

    def invoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        """Generate a tool-aware chat response."""
        ...


class ChatModelLike(Protocol):
    """Subset of the chat model API needed by MCP nodes."""

    def invoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        """Generate a chat response."""
        ...

    def bind_tools(
        self,
        tools: Sequence[BaseTool],
        **kwargs: Any,
    ) -> BoundToolModelLike:
        """Return a model bound to tools."""
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


class MCPClientLike(Protocol):
    """Subset of the MCP client API used by the agent."""

    def get_tools(self, *, server_name: str | None = None) -> Awaitable[list[BaseTool]]:
        """Return LangChain-compatible tools from configured MCP servers."""
        ...


MCPClientFactory = Callable[[], MCPClientLike]


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


__all__ = [
    "ChatModelLike",
    "CompressedMCPResearch",
    "MCPClientFactory",
    "MCPClientLike",
    "MCPResearchInput",
    "MCPResearchResult",
    "MCPResearchState",
    "coerce_structured_output",
]
