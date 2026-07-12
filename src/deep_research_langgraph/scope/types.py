"""Shared state and model contracts for the scope workflow."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any, NotRequired, Protocol, Required, TypedDict, cast

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class ScopeInputState(MessagesState):
    """Input state for a scope run."""


class ScopeState(MessagesState):
    """State produced by the scope phase and consumed by later research phases."""

    research_brief: NotRequired[str]
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages]


class ScopeResult(TypedDict, total=False):
    """State-friendly result returned from the session wrapper."""

    messages: Required[list[BaseMessage]]
    research_brief: NotRequired[str]
    supervisor_messages: NotRequired[list[BaseMessage]]


class ClarificationDecision(BaseModel):
    """Structured decision for whether the user must clarify the request."""

    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarifying question."
    )
    question: str = Field(
        default="",
        description="A question to ask the user to clarify the report scope.",
    )
    verification: str = Field(
        default="",
        description="Message confirming that enough context exists to write the brief.",
    )


class ResearchBrief(BaseModel):
    """Structured output containing the generated research brief."""

    research_brief: str = Field(
        min_length=1,
        description="A detailed research brief that will guide the research agent.",
    )


class StructuredOutputRunnable(Protocol):
    """Subset of the structured-output runnable API used by this workflow."""

    def invoke(self, input: Sequence[BaseMessage] | str) -> BaseModel | dict[str, Any]:
        """Execute the structured output call."""
        ...


class ChatModelLike(Protocol):
    """Subset of the chat model API needed by the scope nodes."""

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
