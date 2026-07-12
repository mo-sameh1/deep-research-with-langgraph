from typing import Any, cast

from deep_research_langgraph.settings import Settings


def test_local_ollama_defaults() -> None:
    settings = _settings_without_env()

    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_model == "langgraph-coder"
    assert settings.ollama_num_ctx == 32768
    assert settings.ollama_temperature == 0.2


def test_cloud_and_paid_provider_defaults_are_off() -> None:
    settings = _settings_without_env()

    assert settings.langsmith_tracing is False
    assert settings.langchain_tracing_v2 is False
    assert settings.langsmith_api_key is None
    assert settings.langsmith_project == "deep-research-with-langgraph"
    assert settings.langsmith_endpoint == "https://api.smith.langchain.com"
    assert settings.langsmith_workspace_id is None
    assert settings.tavily_api_key is None
    assert settings.tavily_search_depth == "basic"
    assert settings.tavily_include_answer is False
    assert settings.tavily_include_raw_content is False
    assert settings.openai_api_key is None
    assert settings.anthropic_api_key is None


def _settings_without_env(**overrides: Any) -> Settings:
    return cast(Any, Settings)(_env_file=None, **overrides)
