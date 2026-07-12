"""Session helpers for running the scope graph outside notebooks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import cast

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from deep_research_langgraph.langsmith.metadata import (
    build_trace_metadata,
    build_trace_tags,
    summarize_scope_outputs,
)
from deep_research_langgraph.langsmith.tracing import workflow_root_trace

from .graph import create_default_scope_app
from .types import ScopeResult


@dataclass
class ScopeSession:
    """Small reusable wrapper around the scope graph and message history."""

    graph: CompiledStateGraph = field(default_factory=create_default_scope_app)
    thread_id: str = field(default_factory=lambda: f"scope-{uuid.uuid4().hex[:8]}")
    messages: list[BaseMessage] = field(default_factory=list)

    @property
    def config(self) -> RunnableConfig:
        """Return the runnable config for this session."""

        return {"configurable": {"thread_id": self.thread_id}}

    def add_user_message(self, content: str) -> None:
        """Append a user message to this session."""

        self.messages.append(HumanMessage(content=content))

    def run_turn(self, *, source: str = "cli", trace_enabled: bool | None = None) -> ScopeResult:
        """Run one scoping turn and retain the graph-produced messages."""

        inputs = {"messages": self.messages}
        with workflow_root_trace(
            name="scope.run_turn",
            inputs={"message_count": len(self.messages)},
            metadata=build_trace_metadata(
                module="scope",
                thread_id=self.thread_id,
                source=source,
                phase="scoping",
                state=inputs,
            ),
            tags=build_trace_tags(module="scope", source=source, phase="scoping"),
            enabled=trace_enabled,
        ) as run:
            result = cast(
                ScopeResult,
                self.graph.invoke(inputs, self.config),
            )
            run.end(outputs=summarize_scope_outputs(result))
        self.messages = list(result["messages"])
        return result


__all__ = ["ScopeSession"]
