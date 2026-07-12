from deep_research_langgraph.scope.views import app_html, graph_html


def test_graph_html_embeds_mermaid_source() -> None:
    html = graph_html("graph TD;\nA-->B;")

    assert "mermaid" in html
    assert "A--&gt;B;" in html


def test_app_html_contains_message_api() -> None:
    html = app_html()

    assert "/api/message" in html
    assert "Deep Research Scope" in html
