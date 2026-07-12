from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from deep_research_langgraph.scope.graph import build_scope_graph
from deep_research_langgraph.scope.nodes import ScopeServices
from deep_research_langgraph.scope.types import ClarificationDecision, ResearchBrief


class FakeStructuredRunnable:
    def __init__(self, output: BaseModel) -> None:
        self.output = output

    def invoke(self, input: Sequence[BaseMessage] | str) -> BaseModel:
        return self.output


class FakeChatModel:
    def __init__(
        self,
        clarification: ClarificationDecision,
        brief: ResearchBrief | None = None,
    ) -> None:
        self.clarification = clarification
        self.brief = brief or ResearchBrief(research_brief="Research the requested topic.")

    def invoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        return AIMessage(content="")

    def with_structured_output(
        self,
        schema: type[BaseModel],
        *,
        method: str = "json_schema",
        include_raw: bool = False,
        **kwargs: Any,
    ) -> FakeStructuredRunnable:
        if schema is ClarificationDecision:
            return FakeStructuredRunnable(self.clarification)
        if schema is ResearchBrief:
            return FakeStructuredRunnable(self.brief)
        raise AssertionError(f"Unexpected schema: {schema}")


def test_scope_graph_asks_for_clarification_when_needed() -> None:
    graph = build_scope_graph(
        ScopeServices(
            llm=FakeChatModel(
                ClarificationDecision(
                    need_clarification=True,
                    question="Which companies should I compare?",
                    verification="",
                )
            )
        )
    )

    result = graph.invoke({"messages": [("user", "Compare these tools.")]})

    assert "research_brief" not in result
    assert result["messages"][-1].content == "Which companies should I compare?"


def test_scope_graph_writes_research_brief_when_request_is_clear() -> None:
    graph = build_scope_graph(
        ScopeServices(
            llm=FakeChatModel(
                ClarificationDecision(
                    need_clarification=False,
                    question="",
                    verification="I have enough context to prepare the brief.",
                ),
                ResearchBrief(
                    research_brief=(
                        "I want to compare Gemini and OpenAI Deep Research on "
                        "capabilities, cost, sources, and report quality."
                    )
                ),
            )
        )
    )

    result = graph.invoke({"messages": [("user", "Compare Gemini and OpenAI Deep Research.")]})

    assert result["research_brief"].startswith("I want to compare Gemini")
    assert result["supervisor_messages"][-1].content.endswith(".")
