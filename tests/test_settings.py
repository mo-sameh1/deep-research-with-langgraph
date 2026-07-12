from deep_research_langgraph.settings import Settings


def test_local_ollama_defaults() -> None:
    settings = Settings()

    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_model == "langgraph-coder"
    assert settings.ollama_num_ctx == 32768
    assert settings.ollama_temperature == 0.2


def test_cloud_and_paid_provider_defaults_are_off() -> None:
    settings = Settings()

    assert settings.langsmith_tracing is False
    assert settings.langchain_tracing_v2 is False
    assert settings.langsmith_api_key is None
    assert settings.langsmith_project == "deep-research-with-langgraph"
    assert settings.langsmith_endpoint == "https://api.smith.langchain.com"
    assert settings.langsmith_workspace_id is None
    assert settings.openai_api_key is None
    assert settings.anthropic_api_key is None
