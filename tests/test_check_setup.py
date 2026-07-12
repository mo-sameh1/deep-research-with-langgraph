from deep_research_langgraph.check_setup import _model_names


def test_model_names_include_latest_alias() -> None:
    names = _model_names({"models": [{"name": "langgraph-coder:latest"}]})

    assert "langgraph-coder:latest" in names
    assert "langgraph-coder" in names
