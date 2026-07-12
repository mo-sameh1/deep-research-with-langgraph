"""Session wrapper for running the research supervisor graph."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.langsmith.metadata import (
    build_trace_metadata,
    build_trace_tags,
    summarize_supervisor_outputs,
)
from deep_research_langgraph.langsmith.tracing import workflow_root_trace

from .graph import create_default_supervisor_app
from .types import SupervisorInput, SupervisorResult


@dataclass
class ResearchSupervisorSession:
    """Small reusable wrapper around the supervisor graph."""

    graph: CompiledStateGraph = field(default_factory=create_default_supervisor_app)
    thread_id: str = field(default_factory=lambda: f"research-supervisor-{uuid.uuid4().hex[:8]}")

    @property
    def config(self) -> RunnableConfig:
        """Return runnable config for this session."""

        return {"configurable": {"thread_id": self.thread_id}}

    async def arun(
        self,
        research_brief: str,
        *,
        max_supervisor_iterations: int = 6,
        max_concurrent_researchers: int = 3,
        max_search_iterations: int = 2,
        max_results_per_query: int = 3,
        source: str = "cli",
        trace_enabled: bool | None = None,
    ) -> SupervisorResult:
        """Run the supervisor for one research brief."""

        initial_state: SupervisorInput = {
            "research_brief": research_brief,
            "max_supervisor_iterations": max_supervisor_iterations,
            "max_concurrent_researchers": max_concurrent_researchers,
            "max_search_iterations": max_search_iterations,
            "max_results_per_query": max_results_per_query,
        }
        with workflow_root_trace(
            name="research_supervisor.run",
            inputs={
                "research_brief": research_brief,
                "max_supervisor_iterations": max_supervisor_iterations,
                "max_concurrent_researchers": max_concurrent_researchers,
                "max_search_iterations": max_search_iterations,
                "max_results_per_query": max_results_per_query,
            },
            metadata=build_trace_metadata(
                module="research_supervisor",
                thread_id=self.thread_id,
                source=source,
                phase="supervision",
                state=initial_state,
            ),
            tags=build_trace_tags(
                module="research_supervisor",
                source=source,
                phase="supervision",
            ),
            enabled=trace_enabled,
        ) as run:
            result = await self.graph.ainvoke(initial_state, self.config)
            run.end(outputs=summarize_supervisor_outputs(result))
        return cast(SupervisorResult, result)


__all__ = ["ResearchSupervisorSession"]
