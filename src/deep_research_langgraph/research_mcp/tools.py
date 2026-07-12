"""Local helper tools used alongside MCP tools."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def think_tool(reflection: str) -> str:
    """Record a strategic research reflection after reading local files."""

    return f"Reflection recorded: {reflection}"


__all__ = ["think_tool"]
