"""Session wrapper for running the research graph."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

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
    ) -> ResearchResult:
        """Run research for one scoped brief."""

        initial_state: ResearchInput = {
            "research_brief": research_brief,
            "max_search_iterations": max_search_iterations,
            "max_results_per_query": max_results_per_query,
        }
        result = self.graph.invoke(initial_state, self.config)
        return cast(ResearchResult, result)


__all__ = ["ResearchSession"]
