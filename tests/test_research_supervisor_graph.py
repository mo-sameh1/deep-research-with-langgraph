from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from deep_research_langgraph.research.types import ResearchResult
from deep_research_langgraph.research_supervisor.graph import build_supervisor_graph
from deep_research_langgraph.research_supervisor.nodes import SupervisorServices


class FakeBoundSupervisorModel:
    def __init__(self, outputs: list[AIMessage]) -> None:
        self.outputs = outputs

    async def ainvoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        if not self.outputs:
            raise AssertionError("No fake supervisor outputs left")
        return self.outputs.pop(0)


class FakeSupervisorModel:
    def __init__(self, outputs: list[AIMessage]) -> None:
        self.bound_model = FakeBoundSupervisorModel(outputs)
        self.bound_tool_names: list[str] = []

    def bind_tools(
        self,
        tools: Sequence[BaseTool],
        **kwargs: Any,
    ) -> FakeBoundSupervisorModel:
        self.bound_tool_names = [tool.name for tool in tools]
        return self.bound_model


class FakeResearchRunner:
    def __init__(self) -> None:
        self.topics: list[str] = []

    async def run(
        self,
        research_topic: str,
        *,
        max_search_iterations: int,
        max_results_per_query: int,
    ) -> ResearchResult:
        self.topics.append(research_topic)
        return {
            "research_brief": research_topic,
            "compressed_research": f"Compressed findings for {research_topic}",
            "raw_notes": [
                (
                    f"Raw notes for {research_topic}. "
                    f"search_loops={max_search_iterations}; results={max_results_per_query}"
                )
            ],
        }


@pytest.mark.anyio
async def test_supervisor_graph_delegates_parallel_research_then_completes() -> None:
    model = FakeSupervisorModel(
        [
            AIMessage(
                content="I should run parallel research.",
                tool_calls=[
                    {
                        "name": "think_tool",
                        "args": {"reflection": "This comparison can be split."},
                        "id": "call-think",
                    },
                    {
                        "name": "ConductResearch",
                        "args": {"research_topic": "Research OpenAI coding agents."},
                        "id": "call-openai",
                    },
                    {
                        "name": "ConductResearch",
                        "args": {"research_topic": "Research Anthropic coding agents."},
                        "id": "call-anthropic",
                    },
                ],
            ),
            AIMessage(
                content="The research is complete.",
                tool_calls=[
                    {
                        "name": "ResearchComplete",
                        "args": {},
                        "id": "call-complete",
                    }
                ],
            ),
        ]
    )
    runner = FakeResearchRunner()
    graph = build_supervisor_graph(SupervisorServices(llm=model, research_runner=runner))

    result = await graph.ainvoke(
        {
            "research_brief": "Compare AI coding agents.",
            "max_supervisor_iterations": 4,
            "max_concurrent_researchers": 3,
            "max_search_iterations": 1,
            "max_results_per_query": 2,
        }
    )

    assert model.bound_tool_names == ["ConductResearch", "ResearchComplete", "think_tool"]
    assert runner.topics == [
        "Research OpenAI coding agents.",
        "Research Anthropic coding agents.",
    ]
    assert result["research_iterations"] == 2
    assert result["notes"] == [
        "Compressed findings for Research OpenAI coding agents.",
        "Compressed findings for Research Anthropic coding agents.",
    ]
    assert len(result["raw_notes"]) == 2


@pytest.mark.anyio
async def test_supervisor_graph_respects_concurrent_research_limit() -> None:
    model = FakeSupervisorModel(
        [
            AIMessage(
                content="Run three tasks, but only two should execute.",
                tool_calls=[
                    {
                        "name": "ConductResearch",
                        "args": {"research_topic": "Topic one."},
                        "id": "call-one",
                    },
                    {
                        "name": "ConductResearch",
                        "args": {"research_topic": "Topic two."},
                        "id": "call-two",
                    },
                    {
                        "name": "ConductResearch",
                        "args": {"research_topic": "Topic three."},
                        "id": "call-three",
                    },
                ],
            ),
            AIMessage(
                content="Complete.",
                tool_calls=[{"name": "ResearchComplete", "args": {}, "id": "done"}],
            ),
        ]
    )
    runner = FakeResearchRunner()
    graph = build_supervisor_graph(SupervisorServices(llm=model, research_runner=runner))

    result = await graph.ainvoke(
        {
            "research_brief": "Compare three topics.",
            "max_concurrent_researchers": 2,
        }
    )

    assert runner.topics == ["Topic one.", "Topic two."]
    assert len(result["notes"]) == 2


@pytest.mark.anyio
async def test_supervisor_graph_ends_when_model_calls_research_complete_first() -> None:
    model = FakeSupervisorModel(
        [
            AIMessage(
                content="No more research needed.",
                tool_calls=[
                    {
                        "name": "ResearchComplete",
                        "args": {},
                        "id": "call-complete",
                    }
                ],
            )
        ]
    )
    runner = FakeResearchRunner()
    graph = build_supervisor_graph(SupervisorServices(llm=model, research_runner=runner))

    result = await graph.ainvoke({"research_brief": "Use existing context."})

    assert runner.topics == []
    assert result.get("notes", []) == []
    assert result["research_iterations"] == 1
