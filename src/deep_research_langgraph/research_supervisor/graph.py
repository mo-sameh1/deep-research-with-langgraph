"""Graph assembly for the multi-agent research supervisor."""

from __future__ import annotations

from typing import cast

from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.models import get_chat_model

from .nodes import (
    GraphResearchAgentRunner,
    SupervisorNode,
    SupervisorServices,
    SupervisorToolsNode,
)
from .types import (
    ResearchAgentRunner,
    SupervisorInput,
    SupervisorModelLike,
    SupervisorResult,
    SupervisorState,
)


def build_supervisor_graph(services: SupervisorServices) -> CompiledStateGraph:
    """Build the course-style research supervisor graph."""

    builder = StateGraph(
        SupervisorState,
        input_schema=SupervisorInput,
        output_schema=SupervisorResult,
    )
    builder.add_node("supervisor", SupervisorNode(services))
    builder.add_node("supervisor_tools", SupervisorToolsNode(services))
    builder.add_edge(START, "supervisor")
    return builder.compile()


def create_default_supervisor_services(
    *,
    model: SupervisorModelLike | None = None,
    research_runner: ResearchAgentRunner | None = None,
) -> SupervisorServices:
    """Create default services using local Ollama and the existing research graph."""

    return SupervisorServices(
        llm=model or cast(SupervisorModelLike, get_chat_model()),
        research_runner=research_runner or GraphResearchAgentRunner(),
    )


def create_default_supervisor_app() -> CompiledStateGraph:
    """Create a runnable supervisor graph."""

    return build_supervisor_graph(create_default_supervisor_services())


__all__ = [
    "build_supervisor_graph",
    "create_default_supervisor_app",
    "create_default_supervisor_services",
]
