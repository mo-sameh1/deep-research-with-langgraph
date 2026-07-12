# ruff: noqa: E501
"""Mermaid diagrams for the research supervisor."""

from __future__ import annotations

from .graph import create_default_supervisor_app


def compiled_supervisor_mermaid() -> str:
    """Return the actual compiled LangGraph Mermaid graph."""

    return create_default_supervisor_app().get_graph(xray=True).draw_mermaid()


def expanded_supervisor_mermaid() -> str:
    """Return a teaching diagram that expands the supervisor_tools node internals."""

    return """---
config:
  flowchart:
    curve: linear
---
flowchart TD
    start([__start__])
    supervisor["supervisor<br/>Local Ollama lead researcher<br/>binds ConductResearch, ResearchComplete, think_tool"]
    supervisor_tools{"supervisor_tools<br/>inspect latest tool calls"}
    think["think_tool<br/>record strategic reflection"]
    fanout{"ConductResearch calls<br/>up to max_concurrent_researchers"}
    subagent1["research sub-agent<br/>fresh research graph state"]
    subagent2["research sub-agent<br/>fresh research graph state"]
    subagent3["research sub-agent<br/>fresh research graph state"]
    gather["collect compressed_research<br/>as ConductResearch ToolMessages"]
    finish["extract delegated notes<br/>for later report writer"]
    end([__end__])

    start --> supervisor
    supervisor --> supervisor_tools
    supervisor_tools -->|think_tool| think
    think --> supervisor_tools
    supervisor_tools -->|ConductResearch| fanout
    fanout --> subagent1
    fanout --> subagent2
    fanout --> subagent3
    subagent1 --> gather
    subagent2 --> gather
    subagent3 --> gather
    gather --> supervisor
    supervisor_tools -->|ResearchComplete, no tool calls, or budget reached| finish
    finish --> end

    classDef default fill:#f2f0ff,stroke:#7d6ad6,color:#1d2433,line-height:1.2
    classDef decision fill:#fff8db,stroke:#d5a400,color:#1d2433,line-height:1.2
    classDef terminal fill:#e8f5ee,stroke:#3b8f62,color:#1d2433,line-height:1.2
    class supervisor_tools,fanout decision
    class start,end terminal
"""


__all__ = ["compiled_supervisor_mermaid", "expanded_supervisor_mermaid"]
