"""Verify that the local-only course setup is ready."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import urlopen

from deep_research_langgraph.langsmith.config import get_langsmith_config
from deep_research_langgraph.settings import Settings


@dataclass(frozen=True)
class CheckResult:
    """One setup check result."""

    name: str
    ok: bool
    detail: str


def _read_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=5) as response:
        payload = response.read().decode("utf-8")
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        msg = f"Expected object response from {url}"
        raise ValueError(msg)
    return parsed


def _model_names(tags_payload: dict[str, Any]) -> set[str]:
    models = tags_payload.get("models", [])
    if not isinstance(models, list):
        return set()

    names: set[str] = set()
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("name")
        if isinstance(name, str):
            names.add(name)
            names.add(name.removesuffix(":latest"))
    return names


def run_checks(settings: Settings) -> list[CheckResult]:
    """Run local setup checks without calling paid or hosted services."""

    langsmith_config = get_langsmith_config(settings)
    results = [
        CheckResult(
            name="settings",
            ok=True,
            detail=(
                f"model={settings.ollama_model}, base_url={settings.ollama_base_url}, "
                f"num_ctx={settings.ollama_num_ctx}"
            ),
        ),
        CheckResult(
            name="cloud tracing",
            ok=not langsmith_config.missing_configuration,
            detail=langsmith_config.summary,
        ),
        CheckResult(
            name="paid provider keys",
            ok=not settings.openai_api_key and not settings.anthropic_api_key,
            detail="not configured",
        ),
        CheckResult(
            name="tavily search",
            ok=bool(settings.tavily_api_key),
            detail="API key configured" if settings.tavily_api_key else "missing TAVILY_API_KEY",
        ),
    ]

    base_url = settings.ollama_base_url.rstrip("/") + "/"
    try:
        version_payload = _read_json(urljoin(base_url, "api/version"))
        version = version_payload.get("version", "unknown")
        results.append(CheckResult("ollama service", True, f"reachable, version={version}"))

        tags_payload = _read_json(urljoin(base_url, "api/tags"))
        names = _model_names(tags_payload)
        model_ok = settings.ollama_model in names
        results.append(
            CheckResult(
                "ollama model",
                model_ok,
                f"{settings.ollama_model} is available"
                if model_ok
                else f"{settings.ollama_model} not found in {sorted(names)}",
            )
        )
    except (TimeoutError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        results.append(CheckResult("ollama service", False, str(exc)))
        results.append(CheckResult("ollama model", False, "skipped because Ollama is unreachable"))

    return results


def main() -> int:
    """CLI entry point."""

    settings = Settings()
    results = run_checks(settings)

    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
