"""Tracing context helpers for optional LangSmith observability."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager, nullcontext
from typing import Any, Literal

from langsmith import get_current_run_tree, trace, tracing_context
from langsmith.run_trees import RunTree

from .client import build_langsmith_client
from .config import DeepResearchLangSmithConfig, get_langsmith_config


def langsmith_tracing_context(
    *,
    config: DeepResearchLangSmithConfig | None = None,
    project_name: str | None = None,
    enabled: bool | None = None,
) -> Any:
    """Return a safe tracing context manager for workflow entrypoints."""

    resolved_config = config or get_langsmith_config()
    if enabled is False:
        return tracing_context(enabled=False)
    if enabled is None:
        tracing_enabled = resolved_config.tracing_active
    else:
        tracing_enabled = enabled and resolved_config.api_key_present
    if not tracing_enabled:
        return nullcontext()
    client = build_langsmith_client(resolved_config)
    if client is None:
        return nullcontext()
    return tracing_context(
        enabled=True,
        client=client,
        project_name=project_name or resolved_config.project,
    )


@contextmanager
def workflow_root_trace(
    *,
    name: str,
    inputs: Mapping[str, Any],
    metadata: Mapping[str, Any],
    tags: list[str],
    config: DeepResearchLangSmithConfig | None = None,
    enabled: bool | None = None,
) -> Iterator[RunTree]:
    """Open a root workflow trace when LangSmith is configured."""

    resolved_config = config or get_langsmith_config()
    with (
        langsmith_tracing_context(
            config=resolved_config,
            enabled=enabled,
            project_name=resolved_config.project,
        ),
        trace(
            name,
            run_type="chain",
            inputs=dict(inputs),
            metadata=dict(metadata),
            tags=tags,
        ) as run,
    ):
        yield run


@contextmanager
def workflow_span(
    *,
    name: str,
    run_type: Literal["tool", "chain", "llm", "retriever", "embedding", "prompt", "parser"],
    inputs: Mapping[str, Any],
    metadata: Mapping[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[RunTree | None]:
    """Create a child span only when a traced parent run exists."""

    if get_current_run_tree() is None:
        yield None
        return
    with trace(
        name,
        run_type=run_type,
        inputs=dict(inputs),
        metadata=dict(metadata or {}),
        tags=tags or [],
    ) as run:
        yield run


__all__ = ["langsmith_tracing_context", "workflow_root_trace", "workflow_span"]
