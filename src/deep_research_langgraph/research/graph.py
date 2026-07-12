"""Graph assembly for the research agent."""

from __future__ import annotations

from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.models import get_chat_model

from .nodes import (
    CompressResearchNode,
    ResearchPlannerNode,
    ResearchServices,
    SearchToolNode,
    should_continue,
)
from .tools import DuckDuckGoLiteSearchClient
from .types import ChatModelLike, ResearchInput, ResearchResult, ResearchState, SearchClient


def build_research_graph(services: ResearchServices) -> CompiledStateGraph:
    """Build the iterative research graph."""

    builder = StateGraph(
        ResearchState,
        input_schema=ResearchInput,
        output_schema=ResearchResult,
    )
    builder.add_node("llm_call", ResearchPlannerNode(services))
    builder.add_node("tool_node", SearchToolNode(services))
    builder.add_node("compress_research", CompressResearchNode(services))

    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges(
        "llm_call",
        should_continue,
        {
            "tool_node": "tool_node",
            "compress_research": "compress_research",
        },
    )
    builder.add_edge("tool_node", "llm_call")
    builder.add_edge("compress_research", END)

    return builder.compile()


def create_default_research_services(
    *,
    model: ChatModelLike | None = None,
    search_client: SearchClient | None = None,
) -> ResearchServices:
    """Create default services using local Ollama and free web search."""

    return ResearchServices(
        llm=model or cast(ChatModelLike, get_chat_model()),
        search_client=search_client or DuckDuckGoLiteSearchClient(),
    )


def create_default_research_app() -> CompiledStateGraph:
    """Create a runnable local-first research graph."""

    return build_research_graph(create_default_research_services())


__all__ = [
    "build_research_graph",
    "create_default_research_app",
    "create_default_research_services",
]
