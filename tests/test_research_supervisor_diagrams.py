from deep_research_langgraph.research_supervisor.diagrams import expanded_supervisor_mermaid


def test_expanded_supervisor_mermaid_shows_tool_internals() -> None:
    mermaid = expanded_supervisor_mermaid()

    assert "supervisor_tools" in mermaid
    assert "think_tool" in mermaid
    assert "ConductResearch" in mermaid
    assert "research sub-agent" in mermaid
    assert "ResearchComplete" in mermaid
