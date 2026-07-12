"""Graph assembly for the MCP research agent."""

from __future__ import annotations

from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.models import get_chat_model

from .config import create_mcp_client
from .nodes import (
    CompressMCPResearchNode,
    MCPPlannerNode,
    MCPResearchServices,
    MCPToolNode,
    should_continue,
)
from .types import (
    ChatModelLike,
    MCPClientFactory,
    MCPResearchInput,
    MCPResearchResult,
    MCPResearchState,
)


def build_mcp_research_graph(services: MCPResearchServices) -> CompiledStateGraph:
    """Build the MCP local-file research graph."""

    builder = StateGraph(
        MCPResearchState,
        input_schema=MCPResearchInput,
        output_schema=MCPResearchResult,
    )
    builder.add_node("llm_call", MCPPlannerNode(services))
    builder.add_node("tool_node", MCPToolNode(services))
    builder.add_node("compress_research", CompressMCPResearchNode(services))

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


def create_default_mcp_research_services(
    *,
    model: ChatModelLike | None = None,
    compression_model: ChatModelLike | None = None,
    mcp_client_factory: MCPClientFactory | None = None,
) -> MCPResearchServices:
    """Create default services using local Ollama and filesystem MCP."""

    llm = model or cast(ChatModelLike, get_chat_model())
    return MCPResearchServices(
        llm=llm,
        compression_llm=compression_model or llm,
        mcp_client_factory=mcp_client_factory or create_mcp_client,
    )


def create_default_mcp_research_app() -> CompiledStateGraph:
    """Create a runnable MCP local-file research graph."""

    return build_mcp_research_graph(create_default_mcp_research_services())


__all__ = [
    "build_mcp_research_graph",
    "create_default_mcp_research_app",
    "create_default_mcp_research_services",
]
