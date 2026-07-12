"""Compiled graphs exposed to LangGraph Studio."""

from __future__ import annotations

from deep_research_langgraph.research.graph import create_default_research_app
from deep_research_langgraph.research_mcp.graph import create_default_mcp_research_app
from deep_research_langgraph.research_supervisor.graph import create_default_supervisor_app
from deep_research_langgraph.scope.graph import create_default_scope_app

scope_research = create_default_scope_app()
research_agent = create_default_research_app()
research_agent_mcp = create_default_mcp_research_app()
research_agent_supervisor = create_default_supervisor_app()

__all__ = [
    "research_agent",
    "research_agent_mcp",
    "research_agent_supervisor",
    "scope_research",
]
