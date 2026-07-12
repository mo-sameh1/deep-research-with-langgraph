from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from deep_research_langgraph.research.graph import build_research_graph
from deep_research_langgraph.research.nodes import ResearchServices
from deep_research_langgraph.research.types import (
    CompressedResearch,
    ResearchDecision,
    SearchResult,
)


class FakeStructuredRunnable:
    def __init__(self, outputs: list[BaseModel]) -> None:
        self.outputs = outputs

    def invoke(self, input: Sequence[BaseMessage] | str) -> BaseModel:
        if not self.outputs:
            raise AssertionError("No fake outputs left")
        return self.outputs.pop(0)


class FakeChatModel:
    def __init__(self) -> None:
        self.outputs: dict[type[BaseModel], list[BaseModel]] = {}

    def add_output(self, schema: type[BaseModel], output: BaseModel) -> None:
        self.outputs.setdefault(schema, []).append(output)

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
        return FakeStructuredRunnable(self.outputs[schema])


class FakeSearchClient:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        self.queries.append(query)
        return [
            SearchResult(
                title="LangGraph docs",
                url="https://langchain-ai.github.io/langgraph/",
                snippet="LangGraph supports stateful agents.",
            )
        ][:max_results]


def test_research_graph_searches_then_compresses() -> None:
    model = FakeChatModel()
    model.add_output(
        ResearchDecision,
        ResearchDecision(
            reflection="Need official docs.",
            enough_information=False,
            search_queries=["LangGraph persistence interrupts checkpoints"],
        ),
    )
    model.add_output(
        ResearchDecision,
        ResearchDecision(
            reflection="Enough evidence.",
            enough_information=True,
            search_queries=[],
        ),
    )
    model.add_output(
        CompressedResearch,
        CompressedResearch(
            compressed_research=(
                "LangGraph has persistence features that allow applications to "
                "save graph state, resume work, and support human-in-the-loop "
                "interrupt flows with checkpointers. These notes are long enough "
                "to represent a useful compressed research summary without "
                "triggering the extractive fallback."
            )
        ),
    )
    search_client = FakeSearchClient()
    graph = build_research_graph(ResearchServices(llm=model, search_client=search_client))

    result = graph.invoke(
        {
            "research_brief": "Research LangGraph persistence.",
            "max_search_iterations": 2,
            "max_results_per_query": 1,
        }
    )

    assert search_client.queries == ["LangGraph persistence interrupts checkpoints"]
    assert result["compressed_research"].startswith("LangGraph has persistence features")
    assert result["raw_notes"]


def test_research_graph_can_compress_without_searching() -> None:
    model = FakeChatModel()
    model.add_output(
        ResearchDecision,
        ResearchDecision(
            reflection="The brief is already answerable from provided context.",
            enough_information=True,
            search_queries=[],
        ),
    )
    model.add_output(
        CompressedResearch,
        CompressedResearch(compressed_research="No extra search was required."),
    )
    search_client = FakeSearchClient()
    graph = build_research_graph(ResearchServices(llm=model, search_client=search_client))

    result = graph.invoke({"research_brief": "Use provided context only."})

    assert search_client.queries == []
    assert result["compressed_research"] == "No extra search was required."


def test_research_graph_falls_back_when_compression_is_too_short() -> None:
    model = FakeChatModel()
    model.add_output(
        ResearchDecision,
        ResearchDecision(
            reflection="Search for official docs.",
            enough_information=False,
            search_queries=["LangGraph docs"],
        ),
    )
    model.add_output(
        ResearchDecision,
        ResearchDecision(
            reflection="Enough evidence.",
            enough_information=True,
            search_queries=[],
        ),
    )
    model.add_output(
        CompressedResearch,
        CompressedResearch(compressed_research="Too short."),
    )
    graph = build_research_graph(ResearchServices(llm=model, search_client=FakeSearchClient()))

    result = graph.invoke({"research_brief": "Research LangGraph docs."})

    assert "Research findings gathered from local web search" in result["compressed_research"]
    assert result["key_sources"]
