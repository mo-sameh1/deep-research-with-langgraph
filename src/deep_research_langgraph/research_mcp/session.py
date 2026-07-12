"""Session wrapper for running the MCP research graph."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.langsmith.metadata import (
    build_trace_metadata,
    build_trace_tags,
    summarize_mcp_research_outputs,
)
from deep_research_langgraph.langsmith.tracing import workflow_root_trace

from .graph import create_default_mcp_research_app
from .types import MCPResearchInput, MCPResearchResult


@dataclass
class MCPResearchSession:
    """Small reusable wrapper around the MCP research graph."""

    graph: CompiledStateGraph = field(default_factory=create_default_mcp_research_app)
    thread_id: str = field(default_factory=lambda: f"research-mcp-{uuid.uuid4().hex[:8]}")

    @property
    def config(self) -> RunnableConfig:
        """Return runnable config for this session."""

        return {"configurable": {"thread_id": self.thread_id}}

    def run(
        self,
        research_brief: str,
        *,
        max_tool_call_iterations: int = 6,
        source: str = "cli",
        trace_enabled: bool | None = None,
    ) -> MCPResearchResult:
        """Run MCP research from synchronous contexts."""

        return asyncio.run(
            self.arun(
                research_brief,
                max_tool_call_iterations=max_tool_call_iterations,
                source=source,
                trace_enabled=trace_enabled,
            )
        )

    async def arun(
        self,
        research_brief: str,
        *,
        max_tool_call_iterations: int = 6,
        source: str = "cli",
        trace_enabled: bool | None = None,
    ) -> MCPResearchResult:
        """Run MCP research for one local-file question."""

        initial_state: MCPResearchInput = {
            "research_brief": research_brief,
            "max_tool_call_iterations": max_tool_call_iterations,
        }
        with workflow_root_trace(
            name="research_mcp.run",
            inputs={
                "research_brief": research_brief,
                "max_tool_call_iterations": max_tool_call_iterations,
            },
            metadata=build_trace_metadata(
                module="research_mcp",
                thread_id=self.thread_id,
                source=source,
                phase="mcp_research",
                state=initial_state,
            ),
            tags=build_trace_tags(
                module="research_mcp",
                source=source,
                phase="mcp_research",
            ),
            enabled=trace_enabled,
        ) as run:
            result = await self.graph.ainvoke(initial_state, self.config)
            run.end(outputs=summarize_mcp_research_outputs(result))
        return cast(MCPResearchResult, result)


__all__ = ["MCPResearchSession"]
