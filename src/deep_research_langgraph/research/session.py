"""Session wrapper for running the research graph."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.langsmith.metadata import (
    build_trace_metadata,
    build_trace_tags,
    summarize_research_outputs,
)
from deep_research_langgraph.langsmith.tracing import workflow_root_trace

from .graph import create_default_research_app
from .types import ResearchInput, ResearchResult


@dataclass
class ResearchSession:
    """Small reusable wrapper around the research graph."""

    graph: CompiledStateGraph = field(default_factory=create_default_research_app)
    thread_id: str = field(default_factory=lambda: f"research-{uuid.uuid4().hex[:8]}")

    @property
    def config(self) -> RunnableConfig:
        """Return runnable config for this session."""

        return {"configurable": {"thread_id": self.thread_id}}

    def run(
        self,
        research_brief: str,
        *,
        max_search_iterations: int = 2,
        max_results_per_query: int = 3,
        source: str = "cli",
        trace_enabled: bool | None = None,
    ) -> ResearchResult:
        """Run research for one scoped brief."""

        initial_state: ResearchInput = {
            "research_brief": research_brief,
            "max_search_iterations": max_search_iterations,
            "max_results_per_query": max_results_per_query,
        }
        with workflow_root_trace(
            name="research.run",
            inputs={
                "research_brief": research_brief,
                "max_search_iterations": max_search_iterations,
                "max_results_per_query": max_results_per_query,
            },
            metadata=build_trace_metadata(
                module="research",
                thread_id=self.thread_id,
                source=source,
                phase="research",
                state=initial_state,
            ),
            tags=build_trace_tags(module="research", source=source, phase="research"),
            enabled=trace_enabled,
        ) as run:
            result = self.graph.invoke(initial_state, self.config)
            run.end(outputs=summarize_research_outputs(result))
        return cast(ResearchResult, result)


__all__ = ["ResearchSession"]
