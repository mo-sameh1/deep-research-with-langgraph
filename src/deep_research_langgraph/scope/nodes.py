"""Node implementations for the scope workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langgraph.types import Command

from .dates import get_today_str
from .prompts import (
    CLARIFY_WITH_USER_INSTRUCTIONS,
    WRITE_RESEARCH_BRIEF_INSTRUCTIONS,
)
from .types import (
    ChatModelLike,
    ClarificationDecision,
    ResearchBrief,
    ScopeState,
    coerce_structured_output,
)


@dataclass(frozen=True)
class ScopeServices:
    """External dependencies used by scope nodes."""

    llm: ChatModelLike


@dataclass(frozen=True)
class ClarifyWithUserNode:
    """Decide whether the request is specific enough to produce a brief."""

    services: ScopeServices

    def __call__(self, state: ScopeState) -> Command[Literal["write_research_brief", "__end__"]]:
        structured_llm = self.services.llm.with_structured_output(
            ClarificationDecision,
            method="json_schema",
        )
        prompt = CLARIFY_WITH_USER_INSTRUCTIONS.format(
            messages=get_buffer_string(state["messages"]),
            date=get_today_str(),
        )
        response = coerce_structured_output(
            structured_llm.invoke([HumanMessage(content=prompt)]),
            ClarificationDecision,
        )

        if response.need_clarification:
            return cast(
                Command[Literal["write_research_brief", "__end__"]],
                Command(
                    goto="__end__",
                    update={"messages": [AIMessage(content=response.question)]},
                ),
            )

        return Command(
            goto="write_research_brief",
            update={"messages": [AIMessage(content=response.verification)]},
        )


@dataclass(frozen=True)
class WriteResearchBriefNode:
    """Transform the scoped conversation into a reusable research brief."""

    services: ScopeServices

    def __call__(self, state: ScopeState) -> ScopeState:
        structured_llm = self.services.llm.with_structured_output(
            ResearchBrief,
            method="json_schema",
        )
        prompt = WRITE_RESEARCH_BRIEF_INSTRUCTIONS.format(
            messages=get_buffer_string(state["messages"]),
            date=get_today_str(),
        )
        response = coerce_structured_output(
            structured_llm.invoke([HumanMessage(content=prompt)]),
            ResearchBrief,
        )
        return cast(
            ScopeState,
            {
                "research_brief": response.research_brief,
                "supervisor_messages": [HumanMessage(content=f"{response.research_brief}.")],
            },
        )


__all__ = ["ClarifyWithUserNode", "ScopeServices", "WriteResearchBriefNode"]
