"""Trace metadata helpers for the course workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

WORKFLOW_NAME = "deep-research-with-langgraph"


def build_trace_metadata(
    *,
    module: str,
    thread_id: str,
    source: str,
    phase: str,
    state: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build normalized metadata for root workflow traces."""

    metadata: dict[str, Any] = {
        "workflow_name": WORKFLOW_NAME,
        "workflow_module": module,
        "workflow_source": source,
        "workflow_phase": phase,
        "thread_id": thread_id,
    }
    if state:
        metadata.update(_summarize_state_for_metadata(module=module, state=state))
    if extra:
        metadata.update(extra)
    return {key: value for key, value in metadata.items() if value is not None}


def build_trace_tags(*, module: str, source: str, phase: str) -> list[str]:
    """Build trace tags for filtering in LangSmith."""

    return sorted(
        {
            f"workflow:{WORKFLOW_NAME}",
            f"module:{module}",
            f"source:{source}",
            f"phase:{phase}",
        }
    )


def summarize_scope_outputs(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact scope output payload for trace visualization."""

    return {
        "message_count": len(state.get("messages", [])),
        "has_research_brief": bool(state.get("research_brief")),
        "research_brief": state.get("research_brief"),
    }


def summarize_research_outputs(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact research output payload for trace visualization."""

    return {
        "has_compressed_research": bool(state.get("compressed_research")),
        "raw_note_count": len(state.get("raw_notes", [])),
        "key_source_count": len(state.get("key_sources", [])),
        "search_iterations": state.get("search_iterations"),
        "compressed_research": state.get("compressed_research"),
    }


def summarize_mcp_research_outputs(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact MCP research output payload for trace visualization."""

    return {
        "has_compressed_research": bool(state.get("compressed_research")),
        "raw_note_count": len(state.get("raw_notes", [])),
        "tool_call_iterations": state.get("tool_call_iterations"),
        "compressed_research": state.get("compressed_research"),
    }


def summarize_supervisor_outputs(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact supervisor output payload for trace visualization."""

    return {
        "note_count": len(state.get("notes", [])),
        "raw_note_count": len(state.get("raw_notes", [])),
        "research_iterations": state.get("research_iterations"),
        "notes": state.get("notes", []),
    }


def summarize_full_agent_outputs(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact full-agent output payload for trace visualization."""

    return {
        "has_research_brief": bool(state.get("research_brief")),
        "has_final_report": bool(state.get("final_report")),
        "note_count": len(state.get("notes", [])),
        "raw_note_count": len(state.get("raw_notes", [])),
        "final_report": state.get("final_report"),
        "research_brief": state.get("research_brief"),
    }


def _summarize_state_for_metadata(*, module: str, state: Mapping[str, Any]) -> dict[str, Any]:
    if module == "scope":
        return {
            "message_count": len(state.get("messages", [])),
            "has_research_brief": bool(state.get("research_brief")),
        }
    if module == "research":
        return {
            "max_search_iterations": state.get("max_search_iterations"),
            "max_results_per_query": state.get("max_results_per_query"),
            "search_iterations": state.get("search_iterations"),
        }
    if module == "research_mcp":
        return {
            "max_tool_call_iterations": state.get("max_tool_call_iterations"),
            "tool_call_iterations": state.get("tool_call_iterations"),
        }
    if module == "research_supervisor":
        return {
            "max_supervisor_iterations": state.get("max_supervisor_iterations"),
            "max_concurrent_researchers": state.get("max_concurrent_researchers"),
            "max_search_iterations": state.get("max_search_iterations"),
            "max_results_per_query": state.get("max_results_per_query"),
        }
    if module == "full_agent":
        return {
            "message_count": len(state.get("messages", [])),
            "max_supervisor_iterations": state.get("max_supervisor_iterations"),
            "max_concurrent_researchers": state.get("max_concurrent_researchers"),
            "max_search_iterations": state.get("max_search_iterations"),
            "max_results_per_query": state.get("max_results_per_query"),
        }
    return {}


__all__ = [
    "WORKFLOW_NAME",
    "build_trace_metadata",
    "build_trace_tags",
    "summarize_full_agent_outputs",
    "summarize_mcp_research_outputs",
    "summarize_research_outputs",
    "summarize_scope_outputs",
    "summarize_supervisor_outputs",
]
