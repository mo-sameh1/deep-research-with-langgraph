from deep_research_langgraph.research.views import app_html, graph_html


def test_research_graph_html_embeds_mermaid() -> None:
    html = graph_html("graph TD;\nA-->B;")

    assert "mermaid" in html
    assert "A--&gt;B;" in html


def test_research_app_html_contains_api_endpoint() -> None:
    html = app_html()

    assert "Deep Research Agent" in html
    assert "/api/research" in html
