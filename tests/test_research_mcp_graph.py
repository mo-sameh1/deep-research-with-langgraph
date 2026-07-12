from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel

from deep_research_langgraph.research_mcp.graph import build_mcp_research_graph
from deep_research_langgraph.research_mcp.nodes import MCPResearchServices
from deep_research_langgraph.research_mcp.types import CompressedMCPResearch


@tool
async def read_file(path: str) -> str:
    """Read a fake local research file."""

    return f"Contents of {path}: Blue Bottle was founded in 2002."


class FakeMCPClient:
    async def get_tools(self, *, server_name: str | None = None) -> list[BaseTool]:
        return [read_file]


class FakeBoundToolModel:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="I should inspect the local file.",
                tool_calls=[
                    {
                        "name": "read_file",
                        "args": {"path": "coffee_shops_sf.md"},
                        "id": "call-read-file",
                    }
                ],
            )
        return AIMessage(content="I have enough local-file evidence.")


class FakeToolCallingModel:
    def __init__(self) -> None:
        self.bound_model = FakeBoundToolModel()

    def invoke(self, input: Sequence[BaseMessage] | str) -> AIMessage:
        return AIMessage(content="")

    def bind_tools(self, tools: Sequence[BaseTool], **kwargs: Any) -> FakeBoundToolModel:
        return self.bound_model

    def with_structured_output(
        self,
        schema: type[BaseModel],
        *,
        method: str = "json_schema",
        include_raw: bool = False,
        **kwargs: Any,
    ) -> FakeStructuredRunnable:
        return FakeStructuredRunnable()


class FakeStructuredRunnable:
    def invoke(self, input: Sequence[BaseMessage] | str) -> BaseModel:
        return CompressedMCPResearch(
            compressed_research=(
                "The local file says Blue Bottle was founded in 2002 and is "
                "associated with specialty coffee in San Francisco."
            )
        )


@pytest.mark.anyio
async def test_mcp_research_graph_calls_tool_then_compresses() -> None:
    graph = build_mcp_research_graph(
        MCPResearchServices(
            llm=FakeToolCallingModel(),
            compression_llm=FakeToolCallingModel(),
            mcp_client_factory=FakeMCPClient,
        )
    )

    result = await graph.ainvoke(
        {
            "research_brief": "What does the local file say about Blue Bottle?",
            "max_tool_call_iterations": 3,
        }
    )

    assert "Blue Bottle" in result["compressed_research"]
    assert result["raw_notes"]
    assert result["tool_call_iterations"] == 1


@pytest.mark.anyio
async def test_mcp_research_graph_compresses_when_budget_is_reached() -> None:
    graph = build_mcp_research_graph(
        MCPResearchServices(
            llm=FakeToolCallingModel(),
            compression_llm=FakeToolCallingModel(),
            mcp_client_factory=FakeMCPClient,
        )
    )

    result = await graph.ainvoke(
        {
            "research_brief": "What does the local file say?",
            "max_tool_call_iterations": 0,
        }
    )

    assert result["compressed_research"]
    assert result.get("tool_call_iterations", 0) == 0
