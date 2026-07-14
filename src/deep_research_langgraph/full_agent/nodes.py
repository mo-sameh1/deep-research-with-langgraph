"""Node implementations for the full deep-research agent."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage

from deep_research_langgraph.scope.dates import get_today_str

from .prompts import FINAL_REPORT_GENERATION_PROMPT
from .types import FullAgentState, WriterModelLike


@dataclass(frozen=True)
class FullAgentServices:
    """External dependencies used by final full-agent nodes."""

    writer_llm: WriterModelLike


@dataclass(frozen=True)
class FinalReportGenerationNode:
    """Synthesize supervisor notes into a final markdown report."""

    services: FullAgentServices

    async def __call__(self, state: FullAgentState) -> dict[str, object]:
        notes = state.get("notes", [])
        findings = "\n".join(notes)
        final_report_prompt = FINAL_REPORT_GENERATION_PROMPT.format(
            research_brief=state.get("research_brief", ""),
            findings=findings,
            date=get_today_str(),
        )
        final_report = await self.services.writer_llm.ainvoke(
            [HumanMessage(content=final_report_prompt)]
        )
        content = str(final_report.content).strip()
        if not content:
            content = _fallback_final_report(state)
        return {
            "final_report": content,
            "messages": [AIMessage(content="Here is the final report: " + content)],
        }


def _fallback_final_report(state: FullAgentState) -> str:
    research_brief = state.get("research_brief", "").strip() or "Unscoped research request"
    notes = [note for note in state.get("notes", []) if note.strip()]
    if not notes:
        return "\n".join(
            [
                f"# {research_brief}",
                "",
                "The workflow reached final report generation, but no research notes were "
                "collected before the writer model returned an empty response.",
            ]
        )
    return "\n".join(
        [
            f"# {research_brief}",
            "",
            "## Research Findings",
            "",
            "\n\n".join(notes),
        ]
    )


__all__ = ["FinalReportGenerationNode", "FullAgentServices"]
