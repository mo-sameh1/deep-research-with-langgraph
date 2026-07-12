from deep_research_langgraph.research_supervisor.views import app_html, graph_html


def test_supervisor_graph_html_embeds_mermaid() -> None:
    html = graph_html("graph TD;\nA-->B;")

    assert "Research Supervisor Graph" in html
    assert "mermaid" in html
    assert "A--&gt;B;" in html


def test_supervisor_app_html_contains_api_endpoint() -> None:
    html = app_html()

    assert "Research Supervisor" in html
    assert "/api/supervisor" in html
    assert "max_concurrent_researchers" in html
