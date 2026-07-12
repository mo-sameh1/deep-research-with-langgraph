"""LangSmith client helpers."""

from __future__ import annotations

from langsmith import Client

from .config import DeepResearchLangSmithConfig, get_langsmith_config


def build_langsmith_client(
    config: DeepResearchLangSmithConfig | None = None,
) -> Client | None:
    """Build a LangSmith client when credentials are available."""

    resolved_config = config or get_langsmith_config()
    if not resolved_config.api_key_present:
        return None
    return Client(
        api_key=resolved_config.api_key,
        api_url=resolved_config.endpoint,
        workspace_id=resolved_config.workspace_id,
    )


def get_langsmith_client() -> Client | None:
    """Return a configured LangSmith client, if credentials are available."""

    return build_langsmith_client()


__all__ = ["build_langsmith_client", "get_langsmith_client"]
