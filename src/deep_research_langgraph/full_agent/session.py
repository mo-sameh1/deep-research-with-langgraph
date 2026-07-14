"""Session wrapper for running the full deep-research graph."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.langsmith.metadata import (
    build_trace_metadata,
    build_trace_tags,
    summarize_full_agent_outputs,
)
from deep_research_langgraph.langsmith.tracing import workflow_root_trace

from .graph import create_default_full_agent_app
from .types import FullAgentInputState, FullAgentState


@dataclass
class FullAgentSession:
    """Small reusable wrapper around the full deep-research graph."""

    graph: CompiledStateGraph = field(default_factory=create_default_full_agent_app)
    thread_id: str = field(default_factory=lambda: f"full-agent-{uuid.uuid4().hex[:8]}")

    @property
    def config(self) -> RunnableConfig:
        """Return runnable config for this session."""

        return {"configurable": {"thread_id": self.thread_id}}

    async def arun(
        self,
        request: str,
        *,
        max_supervisor_iterations: int = 4,
        max_concurrent_researchers: int = 2,
        max_search_iterations: int = 1,
        max_results_per_query: int = 2,
        source: str = "cli",
        trace_enabled: bool | None = None,
    ) -> FullAgentState:
        """Run the complete workflow for one user request."""

        initial_state: FullAgentInputState = {
            "messages": [HumanMessage(content=request)],
            "max_supervisor_iterations": max_supervisor_iterations,
            "max_concurrent_researchers": max_concurrent_researchers,
            "max_search_iterations": max_search_iterations,
            "max_results_per_query": max_results_per_query,
        }
        with workflow_root_trace(
            name="full_agent.run",
            inputs={
                "request": request,
                "max_supervisor_iterations": max_supervisor_iterations,
                "max_concurrent_researchers": max_concurrent_researchers,
                "max_search_iterations": max_search_iterations,
                "max_results_per_query": max_results_per_query,
            },
            metadata=build_trace_metadata(
                module="full_agent",
                thread_id=self.thread_id,
                source=source,
                phase="full_research",
                state=cast(dict[str, Any], initial_state),
            ),
            tags=build_trace_tags(
                module="full_agent",
                source=source,
                phase="full_research",
            ),
            enabled=trace_enabled,
        ) as run:
            result = await self.graph.ainvoke(initial_state, self.config)
            run.end(outputs=summarize_full_agent_outputs(result))
        return cast(FullAgentState, result)


__all__ = ["FullAgentSession"]
