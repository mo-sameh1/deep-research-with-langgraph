"""Node implementations for the multi-agent research supervisor."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Literal, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import filter_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from deep_research_langgraph.langsmith.metadata import summarize_research_outputs
from deep_research_langgraph.langsmith.tracing import workflow_span
from deep_research_langgraph.research.graph import create_default_research_app
from deep_research_langgraph.research.types import ResearchInput, ResearchResult
from deep_research_langgraph.scope.dates import get_today_str

from .prompts import LEAD_RESEARCHER_PROMPT
from .tools import SUPERVISOR_TOOLS, think_tool
from .types import ResearchAgentRunner, SupervisorModelLike, SupervisorState


@dataclass(frozen=True)
class SupervisorServices:
    """External dependencies used by supervisor nodes."""

    llm: SupervisorModelLike
    research_runner: ResearchAgentRunner


@dataclass(frozen=True)
class GraphResearchAgentRunner:
    """Run the existing research graph as an isolated sub-agent."""

    async def run(
        self,
        research_topic: str,
        *,
        max_search_iterations: int,
        max_results_per_query: int,
    ) -> ResearchResult:
        """Run one delegated research topic."""

        graph = create_default_research_app()
        initial_state: ResearchInput = {
            "research_brief": research_topic,
            "max_search_iterations": max_search_iterations,
            "max_results_per_query": max_results_per_query,
        }
        config = cast(
            RunnableConfig,
            {
                "configurable": {
                    "thread_id": f"research-subagent-{uuid.uuid4().hex[:8]}",
                }
            },
        )
        result = await graph.ainvoke(initial_state, config)
        return cast(ResearchResult, result)


@dataclass(frozen=True)
class SupervisorNode:
    """Coordinate research and decide which supervisor tools to call."""

    services: SupervisorServices

    async def __call__(
        self,
        state: SupervisorState,
    ) -> Command[Literal["supervisor_tools"]]:
        supervisor_messages = list(state.get("supervisor_messages", []))
        messages_to_add: list[BaseMessage] = []
        if not supervisor_messages:
            initial_message = HumanMessage(content=f"{state['research_brief']}.")
            supervisor_messages = [initial_message]
            messages_to_add = [initial_message]

        max_supervisor_iterations = state.get("max_supervisor_iterations", 6)
        max_concurrent_researchers = state.get("max_concurrent_researchers", 3)
        system_message = LEAD_RESEARCHER_PROMPT.format(
            date=get_today_str(),
            max_concurrent_research_units=max_concurrent_researchers,
            max_researcher_iterations=max_supervisor_iterations,
        )
        model_with_tools = self.services.llm.bind_tools(SUPERVISOR_TOOLS)
        response = await model_with_tools.ainvoke(
            [SystemMessage(content=system_message), *supervisor_messages]
        )

        return Command(
            goto="supervisor_tools",
            update={
                "supervisor_messages": [*messages_to_add, response],
                "research_iterations": state.get("research_iterations", 0) + 1,
                "max_supervisor_iterations": max_supervisor_iterations,
                "max_concurrent_researchers": max_concurrent_researchers,
                "max_search_iterations": state.get("max_search_iterations", 2),
                "max_results_per_query": state.get("max_results_per_query", 3),
            },
        )


@dataclass(frozen=True)
class SupervisorToolsNode:
    """Execute supervisor tool calls and collect sub-agent findings."""

    services: SupervisorServices

    async def __call__(
        self,
        state: SupervisorState,
    ) -> Command[Literal["supervisor", "__end__"]]:
        supervisor_messages = list(state.get("supervisor_messages", []))
        if not supervisor_messages:
            return _end_command(state)

        most_recent_message = supervisor_messages[-1]
        tool_calls = _tool_calls(most_recent_message)
        if _should_end(state=state, tool_calls=tool_calls):
            return _end_command(state)

        tool_messages: list[ToolMessage] = []
        raw_notes: list[str] = []

        try:
            think_tool_calls = [
                tool_call for tool_call in tool_calls if tool_call["name"] == "think_tool"
            ]
            conduct_research_calls = [
                tool_call for tool_call in tool_calls if tool_call["name"] == "ConductResearch"
            ][: state.get("max_concurrent_researchers", 3)]

            for tool_call in think_tool_calls:
                observation = think_tool.invoke(tool_call.get("args", {}))
                tool_messages.append(
                    ToolMessage(
                        content=str(observation),
                        name="think_tool",
                        tool_call_id=str(tool_call["id"]),
                    )
                )

            if conduct_research_calls:
                research_results = await asyncio.gather(
                    *[
                        _conduct_research(
                            runner=self.services.research_runner,
                            tool_call=tool_call,
                            max_search_iterations=state.get("max_search_iterations", 2),
                            max_results_per_query=state.get("max_results_per_query", 3),
                        )
                        for tool_call in conduct_research_calls
                    ]
                )

                for result, tool_call in zip(
                    research_results,
                    conduct_research_calls,
                    strict=False,
                ):
                    compressed = result.get(
                        "compressed_research",
                        "Error synthesizing research report.",
                    )
                    tool_messages.append(
                        ToolMessage(
                            content=compressed,
                            name="ConductResearch",
                            tool_call_id=str(tool_call["id"]),
                        )
                    )
                    raw_notes.append("\n".join(result.get("raw_notes", [])))
        except Exception as exc:
            return cast(
                Command[Literal["supervisor", "__end__"]],
                Command(
                    goto=END,
                    update={
                        "notes": get_notes_from_tool_calls(supervisor_messages),
                        "raw_notes": [f"Supervisor tool execution failed: {exc}"],
                    },
                ),
            )

        return Command(
            goto="supervisor",
            update={
                "supervisor_messages": tool_messages,
                "raw_notes": [note for note in raw_notes if note],
            },
        )


def get_notes_from_tool_calls(messages: list[BaseMessage]) -> list[str]:
    """Extract compressed research findings from ConductResearch tool messages."""

    notes: list[str] = []
    for tool_message in filter_messages(messages, include_types=["tool"]):
        if isinstance(tool_message, ToolMessage) and tool_message.name == "ConductResearch":
            notes.append(str(tool_message.content))
    return notes


def _tool_calls(message: BaseMessage) -> list[dict[str, Any]]:
    if isinstance(message, AIMessage):
        return [dict(tool_call) for tool_call in message.tool_calls or []]
    return []


def _should_end(*, state: SupervisorState, tool_calls: list[dict[str, Any]]) -> bool:
    exceeded_iterations = state.get("research_iterations", 0) >= state.get(
        "max_supervisor_iterations",
        6,
    )
    no_tool_calls = not tool_calls
    research_complete = any(tool_call["name"] == "ResearchComplete" for tool_call in tool_calls)
    return exceeded_iterations or no_tool_calls or research_complete


def _end_command(state: SupervisorState) -> Command[Literal["supervisor", "__end__"]]:
    return cast(
        Command[Literal["supervisor", "__end__"]],
        Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(list(state.get("supervisor_messages", []))),
                "research_brief": state.get("research_brief", ""),
            },
        ),
    )


async def _conduct_research(
    *,
    runner: ResearchAgentRunner,
    tool_call: dict[str, Any],
    max_search_iterations: int,
    max_results_per_query: int,
) -> ResearchResult:
    args = tool_call.get("args", {})
    research_topic = str(args.get("research_topic", "")).strip()
    if not research_topic:
        return cast(
            ResearchResult,
            {
                "research_brief": "",
                "compressed_research": "ConductResearch received an empty research topic.",
                "raw_notes": [],
            },
        )

    with workflow_span(
        name="conduct_research",
        run_type="chain",
        inputs={
            "research_topic": research_topic,
            "max_search_iterations": max_search_iterations,
            "max_results_per_query": max_results_per_query,
        },
        metadata={"tool_name": "ConductResearch", "agent_role": "research_subagent"},
        tags=["tool:ConductResearch", "agent:research_subagent"],
    ) as run:
        result = await runner.run(
            research_topic,
            max_search_iterations=max_search_iterations,
            max_results_per_query=max_results_per_query,
        )
        if run is not None:
            run.end(outputs=summarize_research_outputs(result))
        return result


__all__ = [
    "GraphResearchAgentRunner",
    "SupervisorNode",
    "SupervisorServices",
    "SupervisorToolsNode",
    "get_notes_from_tool_calls",
]
