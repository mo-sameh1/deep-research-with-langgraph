from deep_research_langgraph.research_mcp.views import app_html, graph_html


def test_mcp_app_html_mentions_mcp_research() -> None:
    html = app_html()

    assert "MCP Research Agent" in html
    assert "max_tool_call_iterations" in html


def test_mcp_graph_html_embeds_mermaid() -> None:
    html = graph_html("graph TD\nA --> B")

    assert "MCP Research Agent Graph" in html
    assert "mermaid" in html
