from deep_research_langgraph.scope.views import app_html, graph_html
from deep_research_langgraph.scope.web_app import GraphDisplayRequestHandler, GraphDisplayServer


def test_graph_html_embeds_mermaid_source() -> None:
    html = graph_html("graph TD;\nA-->B;")

    assert "mermaid" in html
    assert "A--&gt;B;" in html


def test_app_html_contains_message_api() -> None:
    html = app_html()

    assert "/api/message" in html
    assert "Deep Research Scope" in html


def test_graph_display_server_serves_html() -> None:
    server = GraphDisplayServer(("127.0.0.1", 0), GraphDisplayRequestHandler)

    try:
        assert "Scope Graph" in server.html
        assert "mermaid" in server.html
    finally:
        server.server_close()
