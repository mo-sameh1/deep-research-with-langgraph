"""Session helpers for running the scope graph outside notebooks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import cast

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

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

    def run_turn(self) -> ScopeResult:
        """Run one scoping turn and retain the graph-produced messages."""

        result = cast(
            ScopeResult,
            self.graph.invoke({"messages": self.messages}, self.config),
        )
        self.messages = list(result["messages"])
        return result


__all__ = ["ScopeSession"]
