"""Graph assembly for the scope workflow."""

from __future__ import annotations

from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.models import get_chat_model

from .nodes import ClarifyWithUserNode, ScopeServices, WriteResearchBriefNode
from .types import ChatModelLike, ScopeInputState, ScopeState


def build_scope_graph(services: ScopeServices) -> CompiledStateGraph:
    """Build the two-step scoping graph from the course module."""

    builder = StateGraph(ScopeState, input_schema=ScopeInputState)
    builder.add_node("clarify_with_user", ClarifyWithUserNode(services))
    builder.add_node("write_research_brief", WriteResearchBriefNode(services))

    builder.add_edge(START, "clarify_with_user")
    builder.add_edge("write_research_brief", END)

    return builder.compile()


def create_default_scope_services(*, model: ChatModelLike | None = None) -> ScopeServices:
    """Create default services using the local Ollama model."""

    return ScopeServices(llm=model or cast(ChatModelLike, get_chat_model()))


def create_default_scope_app() -> CompiledStateGraph:
    """Create a runnable local-Ollama scope graph."""

    return build_scope_graph(create_default_scope_services())


__all__ = [
    "build_scope_graph",
    "create_default_scope_app",
    "create_default_scope_services",
]
