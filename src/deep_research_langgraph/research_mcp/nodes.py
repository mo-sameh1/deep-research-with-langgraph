"""Node implementations for the MCP research agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import get_buffer_string
from langchain_core.tools import BaseTool

from deep_research_langgraph.langsmith.tracing import workflow_span
from deep_research_langgraph.scope.dates import get_today_str

from .prompts import COMPRESS_MCP_RESEARCH_PROMPT, MCP_RESEARCH_AGENT_PROMPT
from .tools import think_tool
from .types import (
    ChatModelLike,
    CompressedMCPResearch,
    MCPClientFactory,
    MCPResearchState,
    coerce_structured_output,
)


@dataclass(frozen=True)
class MCPResearchServices:
    """External dependencies used by MCP research nodes."""

    llm: ChatModelLike
    compression_llm: ChatModelLike
    mcp_client_factory: MCPClientFactory


@dataclass(frozen=True)
class MCPPlannerNode:
    """Ask the model to decide which MCP tools to call next."""

    services: MCPResearchServices

    async def __call__(self, state: MCPResearchState) -> MCPResearchState:
        max_iterations = state.get("max_tool_call_iterations", 6)
        current_iteration = state.get("tool_call_iterations", 0)
        if current_iteration >= max_iterations:
            return cast(
                MCPResearchState,
                {
                    "researcher_messages": [
                        AIMessage(
                            content=(
                                "MCP tool-call budget reached. "
                                "Compressing the gathered local-file research."
                            )
                        )
                    ]
                },
            )

        tools = await get_all_tools(self.services.mcp_client_factory)
        model_with_tools = self.services.llm.bind_tools(tools)
        prompt = MCP_RESEARCH_AGENT_PROMPT.format(date=get_today_str())
        history = list(state.get("researcher_messages", [])) or [
            HumanMessage(content=state["research_brief"])
        ]
        messages = [
            SystemMessage(content=prompt),
            *history,
        ]
        response = model_with_tools.invoke(messages)
        return cast(MCPResearchState, {"researcher_messages": [response]})


@dataclass(frozen=True)
class MCPToolNode:
    """Execute MCP and local helper tool calls."""

    services: MCPResearchServices

    async def __call__(self, state: MCPResearchState) -> MCPResearchState:
        messages = state.get("researcher_messages", [])
        if not messages:
            return cast(MCPResearchState, {})
        last_message = messages[-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return cast(MCPResearchState, {})

        tools = await get_all_tools(self.services.mcp_client_factory)
        tools_by_name = {tool.name: tool for tool in tools}
        tool_outputs: list[ToolMessage] = []
        raw_notes: list[str] = []

        for tool_call in last_message.tool_calls:
            tool_name = str(tool_call["name"])
            tool = tools_by_name.get(tool_name)
            if tool is None:
                observation = f"Tool '{tool_name}' is not available."
            else:
                observation = await _invoke_tool(tool=tool, tool_call=tool_call)
            observation_text = str(observation)
            raw_notes.append(f"Tool: {tool_name}\nObservation: {observation_text}")
            tool_outputs.append(
                ToolMessage(
                    content=observation_text,
                    name=tool_name,
                    tool_call_id=str(tool_call["id"]),
                )
            )

        return cast(
            MCPResearchState,
            {
                "researcher_messages": tool_outputs,
                "raw_notes": raw_notes,
                "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
            },
        )


@dataclass(frozen=True)
class CompressMCPResearchNode:
    """Compress MCP tool observations into notes for later report writing."""

    services: MCPResearchServices

    def __call__(self, state: MCPResearchState) -> MCPResearchState:
        structured_llm = self.services.compression_llm.with_structured_output(
            CompressedMCPResearch,
            method="json_schema",
        )
        prompt = COMPRESS_MCP_RESEARCH_PROMPT.format(
            date=get_today_str(),
            research_brief=state["research_brief"],
            messages=get_buffer_string(state.get("researcher_messages", [])),
        )
        compressed = coerce_structured_output(
            structured_llm.invoke([HumanMessage(content=prompt)]),
            CompressedMCPResearch,
        )
        compressed_research = compressed.compressed_research
        if len(compressed_research.strip()) < 80 and state.get("raw_notes"):
            compressed_research = _fallback_compressed_research(state)
        return cast(
            MCPResearchState,
            {
                "compressed_research": compressed_research,
            },
        )


async def get_all_tools(mcp_client_factory: MCPClientFactory) -> list[BaseTool]:
    """Return all MCP tools plus local helper tools."""

    client = mcp_client_factory()
    mcp_tools = await client.get_tools()
    return [*mcp_tools, think_tool]


def should_continue(state: MCPResearchState) -> Literal["tool_node", "compress_research"]:
    """Route to MCP tool execution when the latest model message called tools."""

    messages = state.get("researcher_messages", [])
    if not messages:
        return "compress_research"
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_node"
    return "compress_research"


async def _invoke_tool(*, tool: BaseTool, tool_call: Any) -> object:
    with workflow_span(
        name=f"mcp_tool.{tool.name}",
        run_type="tool",
        inputs={"tool_name": tool.name, "args": tool_call.get("args", {})},
        metadata={"provider": "mcp", "tool_name": tool.name},
        tags=["provider:mcp", f"tool:{tool.name}"],
    ) as run:
        observation = await tool.ainvoke(tool_call.get("args", {}))
        if run is not None:
            run.end(outputs={"observation": str(observation)})
        return observation


def _fallback_compressed_research(state: MCPResearchState) -> str:
    evidence = "\n\n".join(state.get("raw_notes", []))[:5000]
    return "\n".join(
        [
            "MCP local-file research findings.",
            "",
            "Research question:",
            state["research_brief"],
            "",
            "Evidence notes:",
            evidence,
        ]
    )


__all__ = [
    "CompressMCPResearchNode",
    "MCPPlannerNode",
    "MCPResearchServices",
    "MCPToolNode",
    "get_all_tools",
    "should_continue",
]
