"""Tools exposed to the research supervisor model."""

from __future__ import annotations

from langchain_core.tools import tool
from pydantic import BaseModel, Field


@tool
class ConductResearch(BaseModel):
    """Tool for delegating a research task to a specialized sub-agent."""

    research_topic: str = Field(
        description=(
            "The topic to research. Should be a single topic, and should be "
            "described in high detail (at least a paragraph)."
        ),
    )


@tool
class ResearchComplete(BaseModel):
    """Tool for indicating that the research process is complete."""


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Args:
        reflection: Detailed reflection on research progress, findings, gaps, and next steps.
    """

    return f"Reflection recorded: {reflection}"


SUPERVISOR_TOOLS = [ConductResearch, ResearchComplete, think_tool]


__all__ = ["SUPERVISOR_TOOLS", "ConductResearch", "ResearchComplete", "think_tool"]
