"""Verification entrypoint for the repository LangSmith setup."""

from __future__ import annotations

from langsmith.utils import LangSmithError

from .client import build_langsmith_client
from .config import get_langsmith_config


def main() -> int:
    """Verify whether the repository is ready to trace to LangSmith."""

    config = get_langsmith_config()
    print(config.summary)
    print(f"Project: {config.project}")
    print(f"Endpoint: {config.endpoint}")
    print(f"Workspace ID configured: {bool(config.workspace_id)}")

    if config.missing_configuration:
        print("Missing configuration:")
        for item in config.missing_configuration:
            print(f"- {item}")
        return 1

    client = build_langsmith_client(config)
    if client is None:
        print("No API key configured. Verification stopped before any network call.")
        return 0

    try:
        list(client.list_projects(limit=1))
    except LangSmithError as exc:
        print(f"LangSmith verification failed: {exc}")
        return 1

    print("LangSmith client authenticated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
