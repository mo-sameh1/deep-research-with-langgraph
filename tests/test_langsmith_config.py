from deep_research_langgraph.langsmith.config import get_langsmith_config
from deep_research_langgraph.settings import Settings


def test_langsmith_config_stays_inactive_by_default() -> None:
    config = get_langsmith_config(Settings())

    assert config.tracing_enabled is False
    assert config.tracing_active is False
    assert config.missing_configuration == []


def test_langsmith_config_requires_api_key_when_tracing_is_enabled() -> None:
    config = get_langsmith_config(Settings(langsmith_tracing=True))

    assert config.tracing_enabled is True
    assert config.tracing_active is False
    assert config.missing_configuration == ["LANGSMITH_API_KEY"]


def test_langchain_tracing_v2_also_enables_langsmith_config() -> None:
    config = get_langsmith_config(
        Settings(
            langchain_tracing_v2=True,
            langsmith_api_key="lsv2-test",
            langsmith_workspace_id=" ",
        )
    )

    assert config.tracing_enabled is True
    assert config.tracing_active is True
    assert config.workspace_id is None
