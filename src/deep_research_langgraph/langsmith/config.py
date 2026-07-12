"""Typed LangSmith configuration for local-first course modules."""

from __future__ import annotations

from dataclasses import dataclass

from deep_research_langgraph.settings import Settings, get_settings


@dataclass(frozen=True)
class DeepResearchLangSmithConfig:
    """Resolved LangSmith settings for scoping and research runs."""

    tracing_enabled: bool
    api_key: str | None
    project: str
    endpoint: str
    workspace_id: str | None

    @property
    def api_key_present(self) -> bool:
        """Return whether an API key is available for authenticated operations."""

        return bool(self.api_key)

    @property
    def tracing_active(self) -> bool:
        """Return whether traces can be sent for this process."""

        return self.tracing_enabled and self.api_key_present

    @property
    def missing_configuration(self) -> list[str]:
        """Return missing variables that block requested tracing."""

        missing: list[str] = []
        if self.tracing_enabled and not self.api_key_present:
            missing.append("LANGSMITH_API_KEY")
        return missing

    @property
    def summary(self) -> str:
        """Return a short human-readable status line."""

        if self.tracing_active:
            return f"LangSmith tracing enabled for project '{self.project}'."
        if self.tracing_enabled:
            return "LangSmith tracing requested, but configuration is incomplete."
        return "LangSmith tracing disabled; local-only execution is active."


def get_langsmith_config(
    settings: Settings | None = None,
) -> DeepResearchLangSmithConfig:
    """Return normalized LangSmith configuration for this repository."""

    resolved_settings = settings or get_settings()
    api_key = _normalize_optional_text(resolved_settings.langsmith_api_key)
    workspace_id = _normalize_optional_text(resolved_settings.langsmith_workspace_id)
    return DeepResearchLangSmithConfig(
        tracing_enabled=(
            resolved_settings.langsmith_tracing or resolved_settings.langchain_tracing_v2
        ),
        api_key=api_key,
        project=resolved_settings.langsmith_project.strip(),
        endpoint=resolved_settings.langsmith_endpoint.strip(),
        workspace_id=workspace_id,
    )


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


__all__ = ["DeepResearchLangSmithConfig", "get_langsmith_config"]
