"""Research agent module for gathering context from a research brief."""

from .graph import build_research_graph, create_default_research_app
from .session import ResearchSession
from .types import CompressedResearch, ResearchDecision, ResearchResult, SearchResult

__all__ = [
    "CompressedResearch",
    "ResearchDecision",
    "ResearchResult",
    "ResearchSession",
    "SearchResult",
    "build_research_graph",
    "create_default_research_app",
]
